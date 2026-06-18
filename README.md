# TrafficSarathi - AI Traffic Image Analysis

TrafficSarathi is an AI-based traffic image analysis system for detecting, classifying, documenting, and reviewing traffic violations from photographic evidence. It combines OpenCV preprocessing, YOLOv8 object detection, rule/heuristic violation detectors, OCR-based license plate recognition, annotated evidence generation, searchable records, analytics, and an evaluation workflow.

## Current Task Coverage

| Task | Status | Implementation |
|---|---|---|
| Image preprocessing | Done | `backend/app/infrastructure/ml/preprocessor.py` performs white balance, low-light CLAHE, rain-streak suppression, shadow normalization, and blur/motion-blur sharpening. |
| Vehicle and road-user detection | Done | `detector.py` runs YOLOv8 at 640 and 1280 resolution, detects vehicles/persons, maps COCO classes to local vehicle categories, and deduplicates boxes. |
| Traffic violation detection | Done, heuristic | `violation_classifier.py` detects helmet non-compliance, seatbelt non-compliance, triple riding, wrong-side driving, stop-line violation, red-light violation, and illegal parking. Some classes are single-image heuristics and need scenario validation. |
| Violation classification | Done | Each `ViolationResult` carries violation type, severity, confidence, vehicle category, bbox, and source vehicle bbox. Pipeline filters low-confidence results and deduplicates overlaps. |
| License plate recognition | Done | `plate_detector.py` localizes plate-like regions with OpenCV, reads text with EasyOCR by default or Tesseract opt-in, parses Indian registration formats, handles row-aware/two-line OCR, and abstains when unreadable. |
| Evidence generation | Done | `image_annotator.py` draws object, violation, and plate boxes. `DetectionService` stores original/evidence images, metadata, timestamps, and vehicle associations. |
| Analytics and reporting | Done | Dashboard, Analytics, Violation Records, review modal, search/filtering, and backend analytics routes provide records, summaries, trends, and severity/type breakdowns. |
| Performance evaluation | Done | `/api/v1/evaluate` computes Accuracy, Precision, Recall, F1-score, mAP-style class AP, and inference latency against user-supplied ground truth. |

## Important Accuracy Notes

This project is intentionally OCR-first for plates. It does not use an LLM to invent or repair plate numbers. If OCR cannot read a plate confidently, the system leaves it blank.

The violation detectors are designed for single uploaded images, so several classes are necessarily heuristic:

- Seatbelt: only evaluated when a car is close and front-facing enough for the cabin/strap to be visible.
- Illegal parking: uses edge/shoulder position, sharpness, and riderless motorcycle cues because motion is unavailable in one frame.
- Wrong-side: compares vehicle orientation against majority flow and guards against normal opposite-lane oncoming traffic.
- Stop-line: uses Hough-line detection; it requires a visible line in the frame.
- Red-light: detects compact red signal blobs in the upper frame, then flags vehicles past the signal region.

## Pipeline

1. Upload image through `/detect` or `/detect/stream`.
2. Save original image and read it with OpenCV.
3. Preprocess image for lighting, rain, shadows, and blur.
4. Detect vehicles and road users with YOLOv8.
5. Run violation detectors and classify results.
6. Read up to the requested number of plates using OCR.
7. Generate annotated evidence.
8. Persist vehicles, violations, evidence paths, metadata, and timestamps.
9. Display results in the React UI and aggregate them in analytics.

## Violation Types

| Violation | Method | Severity |
|---|---|---|
| Helmet non-compliance | Mounted rider head crop plus helmet model check | High |
| Seatbelt non-compliance | Front-facing, close car windshield/cabin analysis | Medium |
| Triple riding | Motorcycle plus three or more associated persons | High |
| Wrong-side driving | Vehicle orientation outlier against majority road flow | Critical |
| Stop-line violation | Hough stop-line detection plus vehicle position | Medium |
| Red-light violation | Red signal blob detection plus vehicle position | Critical |
| Illegal parking | Shoulder/edge/riderless-vehicle still-image heuristic | Low |

## Architecture

```text
frontend/
  React + TypeScript + Vite + Tailwind
  Dashboard, Detection, Violations, Analytics, AI Analysis, Settings

backend/app/
  presentation/   FastAPI routes and schemas
  service/        Pipeline orchestration and business logic
  domain/         Entities and enums
  data_access/    SQLAlchemy models and repositories
  infrastructure/ ML (YOLOv8), OCR (EasyOCR), storage, annotation
```

## Key Backend Files

- `backend/app/infrastructure/ml/preprocessor.py` - image enhancement.
- `backend/app/infrastructure/ml/detector.py` - YOLOv8 object detection.
- `backend/app/infrastructure/ml/violation_classifier.py` - violation detectors and classification pipeline.
- `backend/app/infrastructure/ml/plate_detector.py` - plate localization, OCR, Indian plate parsing.
- `backend/app/infrastructure/annotation/image_annotator.py` - annotated evidence rendering.
- `backend/app/service/detection_service.py` - full detection workflow, DB persistence, plate-to-vehicle association.
- `backend/app/presentation/routes/evaluation.py` - Accuracy, Precision, Recall, F1, mAP-style evaluation.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/detect` | Run full detection and return JSON. |
| `POST` | `/api/v1/detect/stream` | Run detection with SSE progress events. |
| `GET` | `/api/v1/violations` | List/search/filter violation records. |
| `GET` | `/api/v1/violations/{id}` | Get violation detail. |
| `GET` | `/api/v1/violations/{id}/crop` | Get cropped violation image. |
| `PATCH` | `/api/v1/violations/{id}` | Confirm or dismiss a violation. |
| `GET` | `/api/v1/vehicles/search?plate=` | Search vehicles by plate. |
| `GET` | `/api/v1/analytics/summary` | Summary counters. |
| `GET` | `/api/v1/analytics/by-type` | Violation breakdown by type. |
| `GET` | `/api/v1/analytics/trends?days=30` | Daily trend data. |
| `GET` | `/api/v1/analytics/by-severity` | Severity breakdown. |
| `POST` | `/api/v1/evaluate` | Evaluate an uploaded image against supplied ground-truth classes. |
| `GET` | `/api/v1/evaluate/images` | List stored images available for evaluation. |
| `POST` | `/api/v1/evaluate/images/{id}` | Evaluate a stored DB image against ground truth. |
| `GET` | `/api/v1/files/uploads/{filename}` | Serve original uploads. |
| `GET` | `/api/v1/files/evidence/{filename}` | Serve annotated evidence. |

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### Docker

```bash
docker compose up --build
```

## Evaluation

The evaluation page/API accepts a traffic image and a JSON list of ground-truth violation classes, for example:

```json
["helmet", "triple_riding", "illegal_parking"]
```

The backend reports:

- Accuracy over the seven required violation classes
- Precision
- Recall
- F1-score
- mAP-style class average precision
- True positives, false positives, false negatives
- Inference latency in milliseconds

## OCR Configuration

EasyOCR is the default because it performs better on low-resolution CCTV plates.

Optional environment variables:

```bash
TRAFFICSARATHI_OCR_ENGINE=tesseract
TRAFFICSARATHI_THOROUGH_OCR=1
```

`TRAFFICSARATHI_THOROUGH_OCR=1` enables slower extra passes for difficult motorcycle/two-line plates.

## Known Limitations

- Still images cannot prove motion-dependent violations as reliably as video.
- Seatbelt detection abstains on rear-view or distant cars.
- OCR can confuse visually similar characters such as `M/H`, `2/3`, and `5/6`.
- Very small two-line motorcycle plates can be below OCR resolution.
- GPU is recommended for faster YOLO/OCR inference in a live demo.

## Status Summary

All required task categories are implemented. The most important remaining work is validation on a broader labeled dataset, especially for stop-line, seatbelt, illegal-parking, and wrong-side heuristics.
