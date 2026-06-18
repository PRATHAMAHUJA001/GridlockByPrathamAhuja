import numpy as np

from app.domain.entities import BoundingBox, DetectedObject
from app.domain.enums import VehicleCategory
from app.infrastructure.ml.model_registry import get_model

COCO_TO_CATEGORY = {
    "car": VehicleCategory.CAR,
    "motorcycle": VehicleCategory.MOTORCYCLE,
    "bus": VehicleCategory.BUS,
    "truck": VehicleCategory.TRUCK,
    "bicycle": VehicleCategory.BICYCLE,
    "person": VehicleCategory.UNKNOWN,
}

RELEVANT_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle", "person"}


def _compute_iou(box1: BoundingBox, box2: BoundingBox) -> float:
    x1 = max(box1.x, box2.x)
    y1 = max(box1.y, box2.y)
    x2 = min(box1.x + box1.w, box2.x + box2.w)
    y2 = min(box1.y + box1.h, box2.y + box2.h)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = box1.w * box1.h + box2.w * box2.h - inter
    return inter / union if union > 0 else 0.0

def detect_objects(img: np.ndarray, confidence: float = 0.25) -> list[DetectedObject]:
    model = get_model("vehicle_detector")
    
    # Run dual-resolution inference to catch both large vehicles and small distant objects
    results_640 = model(img, conf=confidence, verbose=False)
    results_1280 = model(img, conf=confidence, imgsz=1280, verbose=False)

    detected = []
    
    # Process both result sets
    for results in [results_640, results_1280]:
        for r in results:
            for box in r.boxes:
                cls_name = r.names[int(box.cls[0])]
                if cls_name not in RELEVANT_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                new_obj = DetectedObject(
                    label=cls_name,
                    category=COCO_TO_CATEGORY.get(cls_name, VehicleCategory.UNKNOWN),
                    bbox=BoundingBox(x=x1, y=y1, w=x2 - x1, h=y2 - y1),
                    confidence=round(float(box.conf[0]), 3),
                )
                
                # NMS deduplication
                is_duplicate = False
                for existing in detected:
                    if existing.label == new_obj.label and _compute_iou(existing.bbox, new_obj.bbox) > 0.5:
                        is_duplicate = True
                        if new_obj.confidence > existing.confidence:
                            existing.bbox = new_obj.bbox
                            existing.confidence = new_obj.confidence
                        break
                
                if not is_duplicate:
                    detected.append(new_obj)

    return detected
