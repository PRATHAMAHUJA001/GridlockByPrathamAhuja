"""Violation-detection evaluation harness (Gridlock Hackathon — Module 8).

Runs the real detection pipeline (preprocess -> YOLO detect -> violation classifier)
on the sample images and reports per-class and overall Precision / Recall / F1 / mAP
against hand-labelled ground truth. License-plate OCR is intentionally SKIPPED here so
the harness runs in a few seconds (YOLO + OpenCV only) and isolates violation accuracy.

Run on the machine that has the ML deps installed (torch / ultralytics):

    cd backend
    python ../scripts/eval_violations.py

Edit GROUND_TRUTH below if you re-label the sample images.
"""
from __future__ import annotations

import os
import sys
import time

# Make the backend package importable whether run from repo root or backend/.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_HERE, "..", "backend")
sys.path.insert(0, os.path.abspath(_BACKEND))

import cv2  # noqa: E402

from app.infrastructure.ml.preprocessor import preprocess  # noqa: E402
from app.infrastructure.ml.detector import detect_objects  # noqa: E402
from app.infrastructure.ml.violation_classifier import ViolationPipeline  # noqa: E402

# ---------------------------------------------------------------------------
# Ground truth: the set of violation TYPES actually present in each image.
# These are the Gridlock Hackathon problem-statement classes. Anything the pipeline reports
# that is NOT in this set counts as a false positive; anything in this set the
# pipeline misses is a false negative.
#
# Sample images are rear-view CCTV, so seatbelt is NOT verifiable (absent here)
# and there is no traffic signal / stop-line / wrong-side in frame.
# ---------------------------------------------------------------------------
_IMG_DIR = os.path.join(_HERE, "..", "data", "sample_images")

GROUND_TRUTH: dict[str, set[str]] = {
    "image2.png": {"helmet", "triple_riding"},
    "image3.png": {"helmet", "triple_riding"},
}

ALL_CLASSES = [
    "helmet", "triple_riding", "seatbelt", "wrong_side",
    "stop_line", "red_light", "illegal_parking",
]


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def main() -> None:
    pipeline = ViolationPipeline()

    # Per-class aggregate counters across all images.
    agg: dict[str, dict[str, int]] = {c: {"tp": 0, "fp": 0, "fn": 0} for c in ALL_CLASSES}
    per_image: list[tuple[str, set[str], set[str], float]] = []

    for fname, gt in GROUND_TRUTH.items():
        path = os.path.join(_IMG_DIR, fname)
        img = cv2.imread(path)
        if img is None:
            print(f"!! could not read {path}; skipping")
            continue

        t0 = time.time()
        processed = preprocess(img)
        objects = detect_objects(processed)
        violations = pipeline.run(processed, objects)
        elapsed = time.time() - t0

        detected = {v.violation_type.value for v in violations}
        per_image.append((fname, gt, detected, elapsed))

        for c in ALL_CLASSES:
            in_gt = c in gt
            in_det = c in detected
            if in_gt and in_det:
                agg[c]["tp"] += 1
            elif in_det and not in_gt:
                agg[c]["fp"] += 1
            elif in_gt and not in_det:
                agg[c]["fn"] += 1

    # ---- Per-image summary ----
    print("\n=== Per-image results ===")
    for fname, gt, det, elapsed in per_image:
        missed = gt - det
        false = det - gt
        print(f"\n{fname}  ({elapsed:.1f}s, {len(det)} type(s) detected)")
        print(f"  ground truth : {sorted(gt)}")
        print(f"  detected     : {sorted(det)}")
        print(f"  missed (FN)  : {sorted(missed) or '—'}")
        print(f"  false (FP)   : {sorted(false) or '—'}")

    # ---- Per-class metrics ----
    print("\n=== Per-class metrics (image-level presence) ===")
    print(f"{'class':16}{'TP':>4}{'FP':>4}{'FN':>4}{'Prec':>8}{'Rec':>8}{'F1':>8}")
    tot_tp = tot_fp = tot_fn = 0
    ap_values: list[float] = []
    for c in ALL_CLASSES:
        tp, fp, fn = agg[c]["tp"], agg[c]["fp"], agg[c]["fn"]
        tot_tp += tp; tot_fp += fp; tot_fn += fn
        p, r, f1 = _prf(tp, fp, fn)
        # AP per class only defined where the class appears in some ground truth.
        if (tp + fn) > 0:
            ap_values.append(r)  # classification AP == recall for present classes
        print(f"{c:16}{tp:>4}{fp:>4}{fn:>4}{p:>8.3f}{r:>8.3f}{f1:>8.3f}")

    # ---- Overall (micro-averaged) ----
    P, R, F1 = _prf(tot_tp, tot_fp, tot_fn)
    mAP = sum(ap_values) / len(ap_values) if ap_values else 0.0
    print("-" * 56)
    print(f"{'OVERALL (micro)':16}{tot_tp:>4}{tot_fp:>4}{tot_fn:>4}{P:>8.3f}{R:>8.3f}{F1:>8.3f}")
    print(f"\nmAP (present classes): {mAP:.3f}")
    print("\nNote: seatbelt/red_light/stop_line/wrong_side absent from these rear-view")
    print("samples — any detection of them is a false positive (precision check).")


if __name__ == "__main__":
    main()
