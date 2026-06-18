from pydantic import BaseModel


class BoundingBoxSchema(BaseModel):
    x: int
    y: int
    w: int
    h: int


class DetectedObjectSchema(BaseModel):
    label: str
    category: str
    bbox: BoundingBoxSchema
    confidence: float


class ViolationResultSchema(BaseModel):
    violation_type: str
    severity: str
    confidence: float
    bbox: BoundingBoxSchema
    vehicle_category: str


class PlateResultSchema(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBoxSchema


class DetectionResponse(BaseModel):
    objects: list[DetectedObjectSchema]
    violations: list[ViolationResultSchema]
    plates: list[PlateResultSchema]
    evidence_url: str
    original_url: str
    total_violations: int
