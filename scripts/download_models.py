"""Download YOLOv8 model weights for the detection pipeline."""
from pathlib import Path
from ultralytics import YOLO

models_dir = Path(__file__).resolve().parent.parent / "backend" / "ml_models"
models_dir.mkdir(exist_ok=True)

print("Downloading YOLOv8s model...")
model = YOLO("yolov8s.pt")
import shutil
src = Path("yolov8s.pt")
if src.exists():
    shutil.move(str(src), str(models_dir / "yolov8s.pt"))
    print(f"Saved to {models_dir / 'yolov8s.pt'}")
else:
    print("Model downloaded by ultralytics to cache. Copying...")
    model.export
    print("Model ready in ultralytics cache, will be loaded automatically.")

print("Done!")
