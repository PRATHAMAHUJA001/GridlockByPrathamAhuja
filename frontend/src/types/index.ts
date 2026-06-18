export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DetectedObject {
  label: string;
  category: string;
  bbox: BoundingBox;
  confidence: number;
}

export interface ViolationResult {
  violation_type: string;
  severity: string;
  confidence: number;
  bbox: BoundingBox;
  vehicle_category: string;
}

export interface PlateResult {
  text: string;
  confidence: number;
  bbox: BoundingBox;
}

export interface DetectionResponse {
  objects: DetectedObject[];
  violations: ViolationResult[];
  plates: PlateResult[];
  evidence_url: string;
  original_url: string;
  total_violations: number;
  processing_time?: number;
  plates_pending?: boolean;
}

export interface ViolationDetail {
  id: string;
  violation_type: string;
  severity: string;
  confidence: number;
  detected_at: string | null;
  status: string;
  location: string | null;
  plate_number: string | null;
  evidence_url?: string;
  original_url?: string;
  vehicle_category?: string;
}

export interface ViolationListItem {
  id: string;
  violation_type: string;
  severity: string;
  confidence: number;
  detected_at: string | null;
  status: string;
  location: string | null;
  plate_number: string | null;
}

export interface ViolationListResponse {
  items: ViolationListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface AnalyticsSummary {
  total_violations: number;
  today_violations: number;
  avg_confidence: number;
  pending_review: number;
}

export interface TypeCount {
  type: string;
  count: number;
  avg_confidence: number;
}

export interface DateCount {
  date: string;
  count: number;
}

export interface SeverityCount {
  severity: string;
  count: number;
}

export interface MetricSet {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  mean_average_precision?: number | null;
}

export interface StoredImageSummary {
  id: string;
  image_type: string;
  width?: number | null;
  height?: number | null;
  uploaded_at?: string | null;
  source?: string | null;
  image_url: string;
}

export interface EvaluationResponse {
  ground_truth: string[];
  cv_detections: string[];
  cv_metrics: MetricSet;
  cv_results: DetectionResponse;
  inference_latency_ms?: number | null;
}
