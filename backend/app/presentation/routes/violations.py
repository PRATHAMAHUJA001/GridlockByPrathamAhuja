from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.data_access.database import get_db
from app.presentation.schemas.violation_schema import (
    UpdateStatusRequest,
    ViolationDetail,
    ViolationListItem,
    ViolationListResponse,
)
from app.service.violation_service import ViolationService

router = APIRouter(prefix="/violations", tags=["violations"])


@router.get("", response_model=ViolationListResponse)
def list_violations(
    violation_type: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = ViolationService(db)
    items, total = service.list_violations(violation_type, severity, status, date_from, date_to, page, limit)
    return ViolationListResponse(
        items=[
            ViolationListItem(
                id=v.id,
                violation_type=v.violation_type,
                severity=v.severity,
                confidence=v.confidence,
                detected_at=v.detected_at,
                status=v.status,
                location=v.location,
                plate_number=v.vehicle.plate_number if v.vehicle else None,
            )
            for v in items
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{violation_id}", response_model=ViolationDetail)
def get_violation(violation_id: str, db: Session = Depends(get_db)):
    service = ViolationService(db)
    v = service.get_violation(violation_id)
    if not v:
        raise HTTPException(status_code=404, detail="Violation not found")
    return ViolationDetail(
        id=v.id,
        violation_type=v.violation_type,
        severity=v.severity,
        confidence=v.confidence,
        detected_at=v.detected_at,
        status=v.status,
        location=v.location,
        plate_number=v.vehicle.plate_number if v.vehicle else None,
        bbox_x=v.bbox_x,
        bbox_y=v.bbox_y,
        bbox_w=v.bbox_w,
        bbox_h=v.bbox_h,
        vehicle_category=v.vehicle.vehicle_category if v.vehicle else None,
        original_image_url=f"/api/v1/files/uploads/{v.original_image.file_path.split('/')[-1].split(chr(92))[-1]}" if v.original_image else None,
        evidence_image_url=f"/api/v1/files/evidence/{v.evidence_image.file_path.split('/')[-1].split(chr(92))[-1]}" if v.evidence_image else None,
        all_violation_types=(v.metadata_ or {}).get("all_violation_types", [v.violation_type]),
    )


@router.get("/{violation_id}/crop")
def get_violation_crop(violation_id: str, db: Session = Depends(get_db)):
    """Return a cropped JPEG of just the violating vehicle region (with a small margin),
    so the review screen shows the specific violation rather than the whole frame."""
    import cv2

    from app.infrastructure.storage.file_storage import read_image

    service = ViolationService(db)
    v = service.get_violation(violation_id)
    if not v or not v.original_image:
        raise HTTPException(status_code=404, detail="Violation or source image not found")

    try:
        img = read_image(v.original_image.file_path)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=400, detail="Could not load source image")

    h_img, w_img = img.shape[:2]
    bx, by, bw, bh = v.bbox_x or 0, v.bbox_y or 0, v.bbox_w or 0, v.bbox_h or 0
    # Generous margin so the plate (below riders) and context are included
    mx = int(bw * 0.3) + 10
    my = int(bh * 0.4) + 10
    x0 = max(0, bx - mx); y0 = max(0, by - my)
    x1 = min(w_img, bx + bw + mx); y1 = min(h_img, by + bh + my)
    crop = img[y0:y1, x0:x1]
    if crop.size == 0:
        crop = img

    ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode crop")
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.patch("/{violation_id}")
def update_violation_status(violation_id: str, req: UpdateStatusRequest, db: Session = Depends(get_db)):
    service = ViolationService(db)
    v = service.update_status(violation_id, req.status)
    if not v:
        raise HTTPException(status_code=404, detail="Violation not found")
    return {"id": v.id, "status": v.status}


