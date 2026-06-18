import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.data_access.database import get_db
from app.presentation.schemas.detection_schema import (
    BoundingBoxSchema,
    DetectedObjectSchema,
    DetectionResponse,
    PlateResultSchema,
    ViolationResultSchema,
)
from app.service.detection_service import DetectionService

router = APIRouter(prefix="/detect", tags=["detection"])


@router.post("/stream")
async def detect_violations_stream(
    file: UploadFile = File(...),
    location: str | None = Form(None),
    max_plates: int = Form(5),
    db: Session = Depends(get_db),
):
    """SSE streaming endpoint — sends real-time progress events."""
    image_bytes = await file.read()
    service = DetectionService(db)

    def event_generator():
        for event in service.process_image_stream(image_bytes, file.filename or "image.jpg", location, max_plates):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=DetectionResponse)
async def detect_violations(
    file: UploadFile = File(...),
    location: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Non-streaming endpoint — returns full JSON result."""
    image_bytes = await file.read()
    service = DetectionService(db)
    result = service.process_image(image_bytes, file.filename or "image.jpg", location)

    return DetectionResponse(
        objects=[
            DetectedObjectSchema(
                label=o.label,
                category=o.category.value,
                bbox=BoundingBoxSchema(x=o.bbox.x, y=o.bbox.y, w=o.bbox.w, h=o.bbox.h),
                confidence=o.confidence,
            )
            for o in result.objects
        ],
        violations=[
            ViolationResultSchema(
                violation_type=v.violation_type.value,
                severity=v.severity.value,
                confidence=v.confidence,
                bbox=BoundingBoxSchema(x=v.bbox.x, y=v.bbox.y, w=v.bbox.w, h=v.bbox.h),
                vehicle_category=v.vehicle_category.value,
            )
            for v in result.violations
        ],
        plates=[
            PlateResultSchema(
                text=p.text,
                confidence=p.confidence,
                bbox=BoundingBoxSchema(x=p.bbox.x, y=p.bbox.y, w=p.bbox.w, h=p.bbox.h),
            )
            for p in result.plates
        ],
        evidence_url=f"/api/v1/files/evidence/{Path(result.evidence_path).name}",
        original_url=f"/api/v1/files/uploads/{Path(result.original_path).name}",
        total_violations=len(result.violations),
    )
