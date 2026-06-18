import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.data_access.database import get_db
from app.data_access.models import Image
from app.domain.enums import ViolationType
from app.presentation.schemas.detection_schema import (
    BoundingBoxSchema,
    DetectedObjectSchema,
    DetectionResponse,
    PlateResultSchema,
    ViolationResultSchema,
)
from app.presentation.schemas.evaluation_schema import (
    EvaluationResponse,
    MetricSet,
    StoredImageSummary,
)
from app.service.detection_service import DetectionService

router = APIRouter(prefix="/evaluate", tags=["evaluation"])


def _build_detection_response(result) -> DetectionResponse:
    """Convert a DetectionOutput into the API DetectionResponse schema."""
    return DetectionResponse(
        objects=[
            DetectedObjectSchema(
                label=o.label, category=o.category.value,
                bbox=BoundingBoxSchema(x=o.bbox.x, y=o.bbox.y, w=o.bbox.w, h=o.bbox.h),
                confidence=o.confidence,
            )
            for o in result.objects
        ],
        violations=[
            ViolationResultSchema(
                violation_type=v.violation_type.value, severity=v.severity.value, confidence=v.confidence,
                bbox=BoundingBoxSchema(x=v.bbox.x, y=v.bbox.y, w=v.bbox.w, h=v.bbox.h),
                vehicle_category=v.vehicle_category.value,
            )
            for v in result.violations
        ],
        plates=[
            PlateResultSchema(
                text=p.text, confidence=p.confidence,
                bbox=BoundingBoxSchema(x=p.bbox.x, y=p.bbox.y, w=p.bbox.w, h=p.bbox.h),
            )
            for p in result.plates
        ],
        evidence_url=f"/api/v1/files/evidence/{Path(result.evidence_path).name}",
        original_url=f"/api/v1/files/uploads/{Path(result.original_path).name}",
        total_violations=len(result.violations),
    )


EVALUATED_CLASSES = {
    ViolationType.HELMET.value,
    ViolationType.SEATBELT.value,
    ViolationType.TRIPLE_RIDING.value,
    ViolationType.WRONG_SIDE.value,
    ViolationType.STOP_LINE.value,
    ViolationType.RED_LIGHT.value,
    ViolationType.ILLEGAL_PARKING.value,
}


def _compute_metrics(detected: set[str], ground_truth: set[str]) -> MetricSet:
    label_space = EVALUATED_CLASSES | detected | ground_truth
    tp = len(detected & ground_truth)
    fp = len(detected - ground_truth)
    fn = len(ground_truth - detected)
    tn = len(label_space - detected - ground_truth)
    accuracy = (tp + tn) / len(label_space) if label_space else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return MetricSet(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


def _compute_map(detected: set[str], ground_truth: set[str]) -> float:
    """Compute mean Average Precision (mAP) across violation classes.

    Since our task is classification (violation type presence/absence) rather than
    spatial bounding-box detection, AP per class is 1.0 if the class was correctly
    detected, 0.0 if missed or false-positive. mAP is the mean across all classes
    present in the ground truth. This is equivalent to recall for classification,
    but we include it separately for the Gridlock Hackathon Module-8 evaluation requirement.
    """
    if not ground_truth:
        return 0.0
    # Per-class AP: 1.0 if detected, 0.0 if missed
    per_class_ap = []
    for gt_class in ground_truth:
        if gt_class in detected:
            per_class_ap.append(1.0)
        else:
            per_class_ap.append(0.0)
    return round(sum(per_class_ap) / len(per_class_ap), 4)


def _image_url(image: Image) -> str:
    filename = Path(image.file_path).name
    folder = "evidence" if image.image_type == "annotated" else "uploads"
    return f"/api/v1/files/{folder}/{filename}"


def _evaluate_bytes(
    image_bytes: bytes,
    filename: str,
    ground_truth: str,
    location: str | None,
    db: Session,
) -> EvaluationResponse:
    gt_list: list[str] = json.loads(ground_truth)
    gt_set = set(gt_list)

    t0 = time.time()
    service = DetectionService(db)
    result = service.process_image(image_bytes, filename, location)
    inference_ms = round((time.time() - t0) * 1000, 1)

    cv_detections = list({v.violation_type.value for v in result.violations})
    cv_set = set(cv_detections)

    cv_metrics = _compute_metrics(cv_set, gt_set)
    cv_metrics.mean_average_precision = _compute_map(cv_set, gt_set)

    return EvaluationResponse(
        ground_truth=gt_list,
        cv_detections=cv_detections,
        cv_metrics=cv_metrics,
        cv_results=_build_detection_response(result),
        inference_latency_ms=inference_ms,
    )


@router.get("/images", response_model=list[StoredImageSummary])
def list_evaluation_images(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    images = (
        db.query(Image)
        .filter(Image.image_type == "original")
        .order_by(Image.uploaded_at.desc())
        .limit(limit)
        .all()
    )
    return [
        StoredImageSummary(
            id=img.id,
            image_type=img.image_type,
            width=img.width,
            height=img.height,
            uploaded_at=img.uploaded_at.isoformat() if img.uploaded_at else None,
            source=img.source,
            image_url=_image_url(img),
        )
        for img in images
    ]


@router.post("", response_model=EvaluationResponse)
async def evaluate(
    file: UploadFile = File(...),
    ground_truth: str = Form(...),
    location: str | None = Form(None),
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()
    return _evaluate_bytes(image_bytes, file.filename or "image.jpg", ground_truth, location, db)


@router.post("/images/{image_id}", response_model=EvaluationResponse)
async def evaluate_existing_image(
    image_id: str,
    ground_truth: str = Form(...),
    location: str | None = Form(None),
    db: Session = Depends(get_db),
):
    image = db.query(Image).filter(Image.id == image_id, Image.image_type == "original").first()
    if not image:
        raise HTTPException(status_code=404, detail="Stored image not found")

    path = Path(image.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored image file missing on disk")

    return _evaluate_bytes(path.read_bytes(), path.name, ground_truth, location, db)
