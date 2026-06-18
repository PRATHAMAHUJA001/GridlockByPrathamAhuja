import json
import time
from typing import Generator

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.data_access.models import Image, Vehicle, Violation
from app.data_access.repositories.image_repo import ImageRepository
from app.data_access.repositories.vehicle_repo import VehicleRepository
from app.data_access.repositories.violation_repo import ViolationRepository
from app.domain.entities import BoundingBox, DetectionOutput, PlateResult, ViolationResult
from app.domain.enums import VIOLATION_SEVERITY_MAP
from app.infrastructure.annotation.image_annotator import annotate_image
from app.infrastructure.ml.detector import detect_objects
from app.infrastructure.ml.plate_detector import (
    detect_plates,
    iter_vehicle_plates,
    vehicle_plate_candidates,
)
from app.infrastructure.ml.preprocessor import preprocess
from app.infrastructure.ml.violation_classifier import ViolationPipeline
from app.infrastructure.storage.file_storage import read_image, save_evidence, save_upload


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class DetectionService:
    def __init__(self, db: Session):
        self.db = db
        self.violation_pipeline = ViolationPipeline()
        self.violation_repo = ViolationRepository(db)
        self.vehicle_repo = VehicleRepository(db)
        self.image_repo = ImageRepository(db)

    def process_image(self, image_bytes: bytes, filename: str, location: str | None = None) -> DetectionOutput:
        """Non-streaming version (kept for backward compat)."""
        result = None
        for _ in self.process_image_stream(image_bytes, filename, location):
            pass
        # The generator stores the final result on self
        return self._last_result

    def process_image_stream(self, image_bytes: bytes, filename: str, location: str | None = None, max_plates: int = 5) -> Generator[str, None, None]:
        """Yields SSE events as the pipeline progresses."""
        t0 = time.time()

        # Step 1: Upload
        yield _sse_event("step", {"step": "upload", "message": "Saving uploaded image...", "progress": 5})
        upload_path = save_upload(image_bytes, filename)
        img = read_image(upload_path)
        h, w = img.shape[:2]
        original_img_record = self.image_repo.create(
            Image(file_path=str(upload_path), image_type="original", width=w, height=h, source="upload")
        )
        yield _sse_event("step", {"step": "upload", "message": f"Image loaded ({w}x{h})", "progress": 10})

        # Step 2: Preprocessing
        yield _sse_event("step", {"step": "preprocess", "message": "Enhancing image quality...", "progress": 15})
        processed = preprocess(img)
        yield _sse_event("step", {"step": "preprocess", "message": "Preprocessing complete", "progress": 20})

        # Step 3: Object Detection
        yield _sse_event("step", {"step": "detection", "message": "Running YOLOv8 object detection...", "progress": 25})
        objects = detect_objects(processed)
        yield _sse_event("step", {
            "step": "detection",
            "message": f"Detected {len(objects)} objects",
            "progress": 45,
            "objects_count": len(objects),
        })

        # Step 4: Violation Classification
        yield _sse_event("step", {"step": "classification", "message": "Classifying violations...", "progress": 50})
        violations = self.violation_pipeline.run(processed, objects)
        yield _sse_event("step", {
            "step": "classification",
            "message": f"Found {len(violations)} violations",
            "progress": 65,
            "violations_count": len(violations),
        })

        # Step 5: License Plate OCR — per-vehicle, with LIVE progress so the user always
        # sees it working and knows exactly when it finishes (one continuous flow, one
        # final result; no ambiguous "is it still running?" gap).
        scan_limit = max(max_plates * 3, max_plates + 5) if max_plates > 0 else None
        total_vehicles = len(vehicle_plate_candidates(objects, img, max_plates=scan_limit))
        yield _sse_event("step", {
            "step": "ocr",
            "message": f"Reading license plates (0/{total_vehicles} vehicles)...",
            "progress": 70,
        })
        plates: list[PlateResult] = []
        for done, total, plate in iter_vehicle_plates(processed, detected_objects=objects, original_img=img, max_plates=max_plates):
            if plate is not None:
                plates.append(plate)
            # Spread OCR across the 70→90 progress band so the bar visibly advances.
            pct = 70 + int(20 * (done / total)) if total else 90
            found = ", ".join(p.text for p in plates) if plates else "scanning"
            yield _sse_event("step", {
                "step": "ocr",
                "message": f"Reading license plates ({done}/{total} vehicles) — {found}",
                "progress": pct,
                "plates_count": len(plates),
            })

        # Step 6: Evidence Generation (now WITH plate boxes).
        yield _sse_event("step", {"step": "evidence", "message": "Generating annotated evidence...", "progress": 92})
        annotated = annotate_image(processed, objects, violations, plates)
        evidence_path = save_evidence(annotated)
        evidence_record = self.image_repo.create(
            Image(file_path=str(evidence_path), image_type="annotated", width=w, height=h, source="generated")
        )

        # Step 7: Persist to DB — one row per physical vehicle, with its matched plate.
        yield _sse_event("step", {"step": "persist", "message": "Saving to database...", "progress": 96})
        plate_vehicle_cache: dict[str, Vehicle] = {}
        for group in self._group_violations_by_vehicle(violations):
            primary = group["primary"]
            members = group["violations"]
            veh_bbox = group["vehicle_bbox"]
            all_types = group["all_types"]

            matched_plate = self._match_plate_to_vehicle(veh_bbox, plates)
            vehicle = None
            if matched_plate:
                if matched_plate.text in plate_vehicle_cache:
                    vehicle = plate_vehicle_cache[matched_plate.text]
                else:
                    vehicle = self.vehicle_repo.find_by_plate(matched_plate.text)
                    if not vehicle:
                        vehicle = self.vehicle_repo.create(
                            Vehicle(
                                plate_number=matched_plate.text,
                                plate_confidence=matched_plate.confidence,
                                vehicle_category=primary.vehicle_category.value,
                            )
                        )
                    plate_vehicle_cache[matched_plate.text] = vehicle
            self.violation_repo.create(
                Violation(
                    violation_type=primary.violation_type.value,
                    severity=primary.severity.value,
                    confidence=primary.confidence,
                    bbox_x=veh_bbox.x,
                    bbox_y=veh_bbox.y,
                    bbox_w=veh_bbox.w,
                    bbox_h=veh_bbox.h,
                    vehicle_id=vehicle.id if vehicle else None,
                    original_image_id=original_img_record.id,
                    evidence_image_id=evidence_record.id,
                    location=location,
                    metadata_={
                        "all_violation_types": all_types,
                        "violation_count": len(members),
                    },
                )
            )

        elapsed = round(time.time() - t0, 2)
        result_data = {
            "objects": [
                {
                    "label": o.label,
                    "category": o.category.value,
                    "bbox": {"x": o.bbox.x, "y": o.bbox.y, "w": o.bbox.w, "h": o.bbox.h},
                    "confidence": o.confidence,
                }
                for o in objects
            ],
            "violations": [
                {
                    "violation_type": v.violation_type.value,
                    "severity": v.severity.value,
                    "confidence": v.confidence,
                    "bbox": {"x": v.bbox.x, "y": v.bbox.y, "w": v.bbox.w, "h": v.bbox.h},
                    "vehicle_category": v.vehicle_category.value,
                }
                for v in violations
            ],
            "plates": [
                {
                    "text": p.text,
                    "confidence": p.confidence,
                    "bbox": {"x": p.bbox.x, "y": p.bbox.y, "w": p.bbox.w, "h": p.bbox.h},
                }
                for p in plates
            ],
            "evidence_url": f"/api/v1/files/evidence/{evidence_path.name}",
            "original_url": f"/api/v1/files/uploads/{upload_path.name}",
            "total_violations": len(violations),
            "processing_time": elapsed,
        }
        self._last_result = DetectionOutput(
            objects=objects,
            violations=violations,
            plates=plates,
            evidence_path=str(evidence_path),
            original_path=str(upload_path),
        )
        yield _sse_event("step", {"step": "done", "message": f"Complete in {elapsed}s", "progress": 100})
        yield _sse_event("result", result_data)

    # ---- vehicle-centric grouping & plate association -------------------------------

    _SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    @staticmethod
    def _bbox_iou(a: BoundingBox, b: BoundingBox) -> float:
        x1 = max(a.x, b.x)
        y1 = max(a.y, b.y)
        x2 = min(a.x + a.w, b.x + b.w)
        y2 = min(a.y + a.h, b.y + b.h)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = a.w * a.h + b.w * b.h - inter
        return inter / union if union > 0 else 0.0

    def _group_violations_by_vehicle(self, violations: list[ViolationResult]) -> list[dict]:
        """Cluster violations that belong to the SAME physical vehicle.

        Two violations share a vehicle when their source-vehicle bboxes overlap strongly
        (IoU > 0.5). This collapses, e.g., a triple-riding violation and the per-rider
        helmet violations on one bike into a single review. Each returned group carries
        its primary (most-severe) violation plus the full list of detected types.
        """
        groups: list[dict] = []
        for v in violations:
            vb = v.vehicle_bbox or v.bbox
            target = None
            for g in groups:
                if self._bbox_iou(vb, g["vehicle_bbox"]) > 0.5:
                    target = g
                    break
            if target is None:
                target = {"vehicle_bbox": vb, "violations": []}
                groups.append(target)
            target["violations"].append(v)

        for g in groups:
            members = g["violations"]
            # Primary = most severe, then highest confidence.
            primary = max(
                members,
                key=lambda x: (self._SEVERITY_RANK.get(x.severity.value, 0), x.confidence),
            )
            g["primary"] = primary
            # Use the primary's vehicle bbox as the canonical region for the crop.
            g["vehicle_bbox"] = primary.vehicle_bbox or primary.bbox
            # Distinct types, primary first, preserving discovery order otherwise.
            seen = set()
            ordered: list[str] = []
            for x in [primary] + members:
                t = x.violation_type.value
                if t not in seen:
                    seen.add(t)
                    ordered.append(t)
            g["all_types"] = ordered
        return groups

    def _match_plate_to_vehicle(self, vehicle_bbox: BoundingBox, plates: list[PlateResult]) -> PlateResult | None:
        """Return the plate that belongs to THIS vehicle, or None.

        Each plate's bbox is its source vehicle's bbox, so we match by bbox overlap with
        the violating vehicle. Requiring real overlap (IoU >= 0.4) guarantees a different
        vehicle's plate across the frame is never wrongly attached — when the vehicle's
        own plate is illegible, no plate exists for it and we correctly abstain ("—").
        """
        if not plates:
            return None
        best, best_iou = None, 0.0
        for p in plates:
            iou = self._bbox_iou(vehicle_bbox, p.bbox)
            if iou > best_iou:
                best, best_iou = p, iou
        return best if best_iou >= 0.4 else None
