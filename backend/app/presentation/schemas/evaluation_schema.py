from pydantic import BaseModel

from app.presentation.schemas.detection_schema import DetectionResponse


class MetricSet(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    mean_average_precision: float | None = None  # mAP, if computed


class StoredImageSummary(BaseModel):
    id: str
    image_type: str
    width: int | None = None
    height: int | None = None
    uploaded_at: str | None = None
    source: str | None = None
    image_url: str


class EvaluationResponse(BaseModel):
    ground_truth: list[str]
    cv_detections: list[str]
    cv_metrics: MetricSet
    cv_results: DetectionResponse
    inference_latency_ms: float | None = None  # total pipeline time in milliseconds
