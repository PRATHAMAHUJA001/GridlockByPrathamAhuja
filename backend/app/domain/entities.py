from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import Severity, VehicleCategory, ViolationType


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    w: int
    h: int


@dataclass
class DetectedObject:
    label: str
    category: VehicleCategory
    bbox: BoundingBox
    confidence: float


@dataclass
class ViolationResult:
    violation_type: ViolationType
    severity: Severity
    confidence: float
    bbox: BoundingBox
    vehicle_category: VehicleCategory
    # The bbox of the SOURCE vehicle this violation belongs to (the motorcycle/car),
    # as opposed to `bbox` which may be a sub-region (e.g. a single rider). Used to
    # group violations per vehicle and to attach the correct plate. Defaults to `bbox`.
    vehicle_bbox: BoundingBox | None = None


@dataclass
class PlateResult:
    text: str
    confidence: float
    bbox: BoundingBox


@dataclass
class DetectionOutput:
    objects: list[DetectedObject] = field(default_factory=list)
    violations: list[ViolationResult] = field(default_factory=list)
    plates: list[PlateResult] = field(default_factory=list)
    evidence_path: str | None = None
    original_path: str | None = None
    processed_at: datetime = field(default_factory=datetime.utcnow)
