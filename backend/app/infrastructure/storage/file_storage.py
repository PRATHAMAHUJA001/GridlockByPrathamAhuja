import uuid
from pathlib import Path

import cv2
import numpy as np

from app.config import settings


def save_upload(image_bytes: bytes, filename: str) -> Path:
    ext = Path(filename).suffix or ".jpg"
    dest = settings.UPLOAD_DIR / f"{uuid.uuid4()}{ext}"
    dest.write_bytes(image_bytes)
    return dest


def save_evidence(img: np.ndarray) -> Path:
    dest = settings.EVIDENCE_DIR / f"{uuid.uuid4()}.jpg"
    cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return dest


def read_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img
