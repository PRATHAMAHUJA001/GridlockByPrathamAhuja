from enum import Enum


class ViolationType(str, Enum):
    HELMET = "helmet"
    SEATBELT = "seatbelt"
    TRIPLE_RIDING = "triple_riding"
    WRONG_SIDE = "wrong_side"
    STOP_LINE = "stop_line"
    RED_LIGHT = "red_light"
    ILLEGAL_PARKING = "illegal_parking"
    SPEED = "speed"
    WRONG_LANE = "wrong_lane"


class VehicleCategory(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    AUTO_RICKSHAW = "auto_rickshaw"
    BUS = "bus"
    TRUCK = "truck"
    BICYCLE = "bicycle"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


VIOLATION_SEVERITY_MAP: dict[ViolationType, Severity] = {
    ViolationType.HELMET: Severity.HIGH,
    ViolationType.SEATBELT: Severity.MEDIUM,
    ViolationType.TRIPLE_RIDING: Severity.HIGH,
    ViolationType.WRONG_SIDE: Severity.CRITICAL,
    ViolationType.STOP_LINE: Severity.MEDIUM,
    ViolationType.RED_LIGHT: Severity.CRITICAL,
    ViolationType.ILLEGAL_PARKING: Severity.LOW,
    ViolationType.SPEED: Severity.HIGH,
    ViolationType.WRONG_LANE: Severity.MEDIUM,
}
