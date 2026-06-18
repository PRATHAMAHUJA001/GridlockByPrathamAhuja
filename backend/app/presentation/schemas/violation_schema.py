from datetime import datetime

from pydantic import BaseModel


class ViolationListItem(BaseModel):
    id: str
    violation_type: str
    severity: str
    confidence: float
    detected_at: datetime | None
    status: str
    location: str | None
    plate_number: str | None

    class Config:
        from_attributes = True


class ViolationDetail(ViolationListItem):
    bbox_x: int | None
    bbox_y: int | None
    bbox_w: int | None
    bbox_h: int | None
    vehicle_category: str | None
    original_image_url: str | None
    evidence_image_url: str | None
    # All violation types detected on this same vehicle (primary type first).
    all_violation_types: list[str] = []


class ViolationListResponse(BaseModel):
    items: list[ViolationListItem]
    total: int
    page: int
    limit: int


class UpdateStatusRequest(BaseModel):
    status: str
