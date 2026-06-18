from ultralytics import YOLO

from app.config import settings

_models: dict[str, YOLO] = {}


def get_model(name: str) -> YOLO:
    if name not in _models:
        if name == "vehicle_detector":
            _models[name] = YOLO(str(settings.ML_MODELS_DIR / "yolov8s.pt"))
        elif name == "plate_detector":
            path = settings.ML_MODELS_DIR / "plate_detect.pt"
            if path.exists():
                _models[name] = YOLO(str(path))
            else:
                _models[name] = YOLO(str(settings.ML_MODELS_DIR / "yolov8s.pt"))
        elif name == "helmet_detector":
            path = settings.ML_MODELS_DIR / "helmet_detect.pt"
            if path.exists():
                _models[name] = YOLO(str(path))
            else:
                _models[name] = YOLO(str(settings.ML_MODELS_DIR / "yolov8s.pt"))
    return _models[name]
