from datetime import datetime

import cv2
import numpy as np

from app.domain.entities import DetectedObject, PlateResult, ViolationResult
from app.domain.enums import Severity

SEVERITY_COLORS = {
    Severity.LOW: (0, 200, 0),
    Severity.MEDIUM: (0, 200, 255),
    Severity.HIGH: (0, 100, 255),
    Severity.CRITICAL: (0, 0, 255),
}

DETECTION_COLOR = (255, 200, 0)
PLATE_COLOR = (255, 255, 0)


def annotate_image(
    img: np.ndarray,
    objects: list[DetectedObject],
    violations: list[ViolationResult],
    plates: list[PlateResult],
) -> np.ndarray:
    annotated = img.copy()

    for obj in objects:
        b = obj.bbox
        cv2.rectangle(annotated, (b.x, b.y), (b.x + b.w, b.y + b.h), DETECTION_COLOR, 1)
        label = f"{obj.label} {obj.confidence:.0%}"
        cv2.putText(annotated, label, (b.x, b.y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, DETECTION_COLOR, 1)

    for v in violations:
        b = v.bbox
        color = SEVERITY_COLORS.get(v.severity, (0, 0, 255))
        cv2.rectangle(annotated, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 3)
        label = f"VIOLATION: {v.violation_type.value} ({v.confidence:.0%})"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(annotated, (b.x, b.y - th - 10), (b.x + tw + 4, b.y), color, -1)
        cv2.putText(annotated, label, (b.x + 2, b.y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    for p in plates:
        b = p.bbox
        cv2.rectangle(annotated, (b.x, b.y), (b.x + b.w, b.y + b.h), PLATE_COLOR, 2)
        if p.text != "UNKNOWN":
            cv2.putText(annotated, p.text, (b.x, b.y + b.h + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, PLATE_COLOR, 2)

    h, w = annotated.shape[:2]
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    cv2.putText(annotated, timestamp, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return annotated
