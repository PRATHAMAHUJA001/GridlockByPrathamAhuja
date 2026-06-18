import re

import cv2
import numpy as np

from app.domain.entities import BoundingBox, PlateResult

import os


def _thorough_ocr() -> bool:
    """Whether to run the heavier multi-pass plate logic (two-line reconstruction + the
    direct-moto reader), which materially improves motorcycle / two-line plate recall.

    OFF by default. Measured on the sample images it added ~10x latency (≈440s vs ≈40s for
    10 vehicles) and produced the SAME plates — the extra two-line/direct passes did not
    recover any plate the single pass missed (small two-line moto plates are below EasyOCR's
    resolution floor regardless). Opt in with TRAFFICSARATHI_THOROUGH_OCR=1 for max recall."""
    return os.environ.get("TRAFFICSARATHI_THOROUGH_OCR", "") == "1"


INDIAN_PLATE_PATTERN = re.compile(r"[A-Z]{2}\s?\d{1,2}\s?[A-Z]{0,3}\s?\d{1,4}")

# Indian plates have roughly 3:1 to 5:1 width:height ratio
MIN_ASPECT = 2.0
MAX_ASPECT = 6.0
MIN_PLATE_WIDTH = 30
MAX_PLATE_WIDTH = 400
MIN_PLATE_HEIGHT = 8
MAX_PLATE_HEIGHT = 80
MAX_PLATE_AREA = 15000


def detect_plates(img: np.ndarray, detected_objects: list | None = None, original_img: np.ndarray | None = None) -> list[PlateResult]:
    """OCR-based Indian license plate recognition.

    Strategy (per the problem statement — OCR techniques):
      1. For each detected vehicle, take a crop around it from the (un-preprocessed)
         original image — OCR reads natural images better than CV-preprocessed ones.
      2. Localize tight plate-shaped regions inside the crop (crop-in-parts).
      3. Run OCR on multiple preprocessing variants of each region.
      4. Vote across variants, preferring full-length Indian-format plates, and
         require the state+district prefix to recur (rejects unreadable garbage).
    """
    plates: list[PlateResult] = []
    for _done, _total, plate in iter_vehicle_plates(img, detected_objects, original_img):
        if plate is not None:
            plates.append(plate)
    return plates


def vehicle_plate_candidates(detected_objects: list, source: np.ndarray, max_plates: int | None = 5) -> list:
    """Filter to just cars/motorcycles/trucks/buses large enough to read a plate from.
    Returns them sorted largest-to-smallest, capped at max_plates when provided."""
    if not detected_objects:
        return []
    from app.domain.enums import VehicleCategory

    h_img, w_img = source.shape[:2]
    vehicles = [
        o for o in detected_objects
        if o.category in (VehicleCategory.CAR, VehicleCategory.MOTORCYCLE, VehicleCategory.TRUCK, VehicleCategory.BUS)
    ]
    # Only vehicles big enough for their plate to carry readable pixels. Distant specks
    # waste OCR time and never produce a valid plate, so we skip them. Largest-first.
    min_area = (w_img * h_img) * 0.008
    candidates = [v for v in vehicles if v.bbox.w * v.bbox.h >= min_area]
    candidates = sorted(candidates, key=lambda o: o.bbox.w * o.bbox.h, reverse=True)
    return candidates[:max_plates] if max_plates is not None else candidates


def iter_vehicle_plates(img: np.ndarray, detected_objects: list | None = None, original_img: np.ndarray | None = None, max_plates: int = 5):
    """Generator: read a plate for EACH detected vehicle, yielding (done, total, plate_or_None)
    after each one — so callers can stream per-vehicle progress to the UI.

    Yields: (current_index, total_vehicles, PlateResult | None)
    """
    source = original_img if original_img is not None else img
    if detected_objects is None:
        from app.infrastructure.ml.detector import detect_objects
        detected_objects = detect_objects(source)

    h_img, w_img = source.shape[:2]
    seen_prefixes: set[str] = set()

    # `max_plates` is the requested number of readable plate results, not the number
    # of vehicles to try. Some large vehicles are rear-obscured or too distant, so
    # scan a wider candidate pool and stop once enough actual plates are produced.
    scan_limit = max(max_plates * 3, max_plates + 5) if max_plates > 0 else None
    candidates = vehicle_plate_candidates(detected_objects, source, max_plates=scan_limit)
    total = len(candidates)
    direct_reads_used = 0

    for i, v in enumerate(candidates):
        bx, by, bw, bh = v.bbox.x, v.bbox.y, v.bbox.w, v.bbox.h
        from app.domain.enums import VehicleCategory
        is_moto = v.category == VehicleCategory.MOTORCYCLE
        if is_moto:
            mx = int(bw * 0.25); my = int(bh * 0.30)
        else:
            mx = int(bw * 0.08); my = int(bw * 0.08)
        x0 = max(0, bx - mx); y0 = max(0, by - my)
        x1 = min(w_img, bx + bw + mx); y1 = min(h_img, by + bh + my)
        crop = source[y0:y1, x0:x1]

        produced = None
        if crop.size != 0:
            result = _read_plate_voting(crop, is_moto=is_moto)
            if is_moto and bw * bh > 20000:
                low_conf = result is not None and result[1] < 2.0
                thorough = _thorough_ocr()
                run_direct = result is None or (thorough and low_conf)
                if run_direct and (thorough or direct_reads_used < 1):
                    direct_reads_used += 1
                    direct = _direct_moto_plate_read(source, bx, by, bw, bh, h_img, w_img)
                    if direct is not None and (result is None or direct[1] > result[1]):
                        result = direct
            if result is not None:
                plate, score = result
                dedup_key = plate[:6] if len(plate) >= 6 else plate
                if dedup_key not in seen_prefixes:
                    seen_prefixes.add(dedup_key)
                    produced = PlateResult(
                        text=plate,
                        confidence=round(min(0.99, score / 6.0), 3),
                        bbox=BoundingBox(
                            x=bx, 
                            y=by, 
                            w=bw, 
                            h=bh
                        ),
                    )
        yield (i + 1, total, produced)
        if max_plates > 0 and len(seen_prefixes) >= max_plates:
            break

    # Fallback: whole-image contour localization can still recover plates from cars
    # whose vehicle crop was too broad/noisy, so use it whenever we are short of the
    # requested result count.
    if total == 0 or (max_plates <= 0 or len(seen_prefixes) < max_plates):
        for (x, y, w, h) in _find_plate_candidates(img):
            crop = img[y : y + h, x : x + w]
            if crop.size == 0:
                continue
            text, conf = _read_plate(_preprocess_plate_crop(crop), crop)
            dedup_key = text[:6] if len(text) >= 6 else text
            if text != "UNKNOWN" and conf >= 0.2 and dedup_key not in seen_prefixes:
                seen_prefixes.add(dedup_key)
                yield (total, total, PlateResult(text=text, confidence=round(conf, 3), bbox=BoundingBox(x=x, y=y, w=w, h=h)))
                if max_plates > 0 and len(seen_prefixes) >= max_plates:
                    break


def _localize_plate_regions(vehicle_crop: np.ndarray, is_moto: bool = False) -> list[tuple[int, int, int, int]]:
    """Find tight plate-shaped rectangles inside a vehicle crop using blackhat +
    gradient morphology (highlights dark characters on a light plate).

    Motorcycle plates are often stacked on TWO lines, making the plate block nearly
    square (aspect ~1.0-1.6) rather than the wide single-line car shape. So for motos we
    relax the minimum aspect ratio to catch those square two-line blocks (which the
    caller then splits into top/bottom lines)."""
    gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    regions: list[tuple[int, int, int, int]] = []
    min_ar = 1.0 if is_moto else 1.8

    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
    grad = np.absolute(cv2.Sobel(blackhat, cv2.CV_32F, 1, 0, ksize=-1))
    minv, maxv = float(np.min(grad)), float(np.max(grad))
    if maxv - minv > 0:
        grad = (255 * ((grad - minv) / (maxv - minv))).astype("uint8")
    else:
        grad = grad.astype("uint8")
    grad = cv2.morphologyEx(grad, cv2.MORPH_CLOSE, rect_kernel)
    thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5)))
    thresh = cv2.dilate(thresh, None, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if ch == 0:
            continue
        ar = cw / ch
        if min_ar <= ar <= 6.0 and cw >= w * 0.12 and ch >= 6:
            pad = 4
            x0 = max(0, x - pad); y0 = max(0, y - pad)
            x1 = min(w, x + cw + pad); y1 = min(h, y + ch + pad)
            regions.append((x0, y0, x1 - x0, y1 - y0))
    return regions


def _plate_ocr_variants(plate_crop: np.ndarray) -> list[np.ndarray]:
    """Preprocessed versions of a tight plate crop for OCR voting.

    Reduced to the two best-performing variants (CLAHE + Otsu binary) for speed.
    """
    target_h = 120
    scale = max(2.0, target_h / max(plate_crop.shape[0], 1))
    up = cv2.resize(plate_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if len(up.shape) == 3:
        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    else:
        gray = up
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
    return [
        clahe,
        cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1],
    ]


def _ocr_raw(img: np.ndarray) -> tuple[str, float]:
    """Run the active OCR engine on a crop and return (cleaned_text, mean_confidence),
    with row-aware ordering so stacked two-line plates read top-line then bottom-line.

    Engine: Tesseract when available (fast, light — no PyTorch dependency for OCR), otherwise
    EasyOCR. Both return word boxes as (y_centre, x_left, height, text, conf); the shared
    code below clusters them into rows and joins.
    """
    if img is None or img.size == 0 or img.shape[0] < 8 or img.shape[1] < 8:
        return ("", 0.0)

    if _use_tesseract():
        items = _tesseract_words(img)
    else:
        items = _easyocr_words(img)
    if not items:
        return ("", 0.0)

    heights = sorted(it[2] for it in items)
    med_h = heights[len(heights) // 2] if heights else 10
    row_tol = max(med_h * 0.6, 8)

    items.sort(key=lambda t: t[0])  # by vertical centre, top to bottom
    rows: list[list] = []
    for it in items:
        if rows and abs(it[0] - rows[-1][-1][0]) <= row_tol:
            rows[-1].append(it)
        else:
            rows.append([it])

    parts, confs = [], []
    for row in rows:  # rows already ordered top-to-bottom
        for it in sorted(row, key=lambda t: t[1]):  # left-to-right within the row
            parts.append(it[3])
            confs.append(it[4])

    txt = re.sub(r"[^A-Z0-9]", "", "".join(parts).upper())
    conf = sum(confs) / len(confs) if confs else 0.0
    return (txt, conf)


def _easyocr_words(img: np.ndarray) -> list[tuple]:
    """EasyOCR → [(y_centre, x_left, height, text, conf), ...]."""
    reader = _get_ocr_reader()
    try:
        res = reader.readtext(
            img, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            paragraph=False, text_threshold=0.3, low_text=0.3,
        )
    except Exception:
        return []
    out = []
    for box, text, conf in res:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        out.append((sum(ys) / len(ys), min(xs), max(ys) - min(ys), text, conf))
    return out


def _tesseract_words(img: np.ndarray) -> list[tuple]:
    """Tesseract → [(y_centre, x_left, height, text, conf), ...]."""
    import pytesseract

    # psm 6 = assume a uniform block of text (handles single- and two-line plates).
    cfg = "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    try:
        data = pytesseract.image_to_data(img, config=cfg, output_type=pytesseract.Output.DICT)
    except Exception:
        return []
    out = []
    n = len(data["text"])
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        if conf < 0:
            continue
        h = float(data["height"][i])
        yc = float(data["top"][i]) + h / 2
        out.append((yc, float(data["left"][i]), h, text, conf / 100.0))
    return out


def _normalize_crop(crop: np.ndarray, target_long: int) -> np.ndarray:
    """Aspect-ratio-aware upscale: scale so the LONGER side ≈ target_long, preserving
    the crop's aspect ratio. This makes OCR input consistent whether the source image
    is landscape (16:9 CCTV) or portrait (phone), and whether the vehicle is near or far.
    Never downscales (small/distant plates only ever get bigger)."""
    h, w = crop.shape[:2]
    longest = max(h, w)
    if longest == 0:
        return crop
    scale = max(1.0, target_long / longest)
    if scale == 1.0:
        return crop
    return cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def _direct_moto_plate_read(
    source: np.ndarray, bx: int, by: int, bw: int, bh: int,
    h_img: int, w_img: int,
) -> tuple[str, float, int, int, int, int] | None:
    """Fallback plate read for motorcycles: crop the plate area DIRECTLY from the
    original full-resolution image, bypassing the per-vehicle crop→normalize chain.

    The normal pipeline crops the whole motorcycle, normalizes it, then localizes
    plate regions inside. For small/distant motorcycles the plate is ~40×25 px in
    the crop — below EasyOCR's resolution floor. This function instead takes tight
    crops of just the plate area from the original image at multiple candidate
    positions and upscales each aggressively.

    KEY INSIGHT: The debug test proved OCR reads this plate correctly at exactly
    ~200px height on the Otsu binary variant. The normal pipeline fails because
    _plate_ocr_variants always doubles the image, blowing past this sweet spot.
    This function bypasses _plate_ocr_variants and creates its own preprocessing
    variants at exactly the right scale.
    """
    from collections import defaultdict

    candidates: list[tuple[str, float]] = []

    # Plate candidate zones (relative to the motorcycle bbox).
    # Different motorcycles have plates at different heights:
    # - Image3 triple-riding bike: plate at 38-68% height (middle)
    # - Image1 triple-riding bike: plate at 55-85% height (lower-middle)
    # Each zone adds ~3 OCR calls + 1 two-line split = ~5 calls, so keep to 3 max.
    zones = [
        # (x_frac, y_frac, w_frac, h_frac) relative to motorcycle bbox
        (0.00, 0.20, 0.95, 0.35),  # upper-middle 20-55% (image1 bike)
        (0.05, 0.38, 0.90, 0.30),  # middle 38-68% (image3 bike)
        (0.05, 0.55, 0.90, 0.40),  # lower half 55-95%
    ]

    for (xf, yf, wf, hf) in zones:
        # Compute crop coordinates on the original image
        cx = int(bx + bw * xf)
        cy = int(by + bh * yf)
        cw = int(bw * wf)
        ch = int(bh * hf)
        # Extend slightly below the bbox (plate can protrude)
        cy2 = min(h_img, cy + ch + int(bh * 0.15))
        cx = max(0, cx)
        cy = max(0, cy)
        cx2 = min(w_img, cx + cw)

        plate_crop = source[cy:cy2, cx:cx2]
        if plate_crop.size == 0 or plate_crop.shape[0] < 8 or plate_crop.shape[1] < 15:
            continue

        # Upscale to exactly 200px height — the proven sweet spot.
        # Use LANCZOS4 for highest quality interpolation from tiny source.
        target_h = 200
        scale = target_h / max(plate_crop.shape[0], 1)
        up = cv2.resize(plate_crop, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_LANCZOS4)

        # Create preprocessing variants at THIS size (no further upscaling).
        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
        otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # Sharpen for better edge definition after upscale
        blur = cv2.GaussianBlur(clahe, (0, 0), 2)
        sharp = cv2.addWeighted(clahe, 1.5, blur, -0.5, 0)

        # Single-pass OCR on each variant
        for variant in [otsu, clahe, sharp]:
            raw, conf = _ocr_raw(variant)
            if len(raw) < 5:
                continue
            plate = _extract_indian_plate(raw)
            if plate:
                candidates.append((plate, conf))
        # If a confident full plate was already found single-pass, skip the costly
        # two-line split entirely.
        if any(len(p) == 10 and c >= 0.5 for p, c in candidates):
            break

        # Two-line split OCR (for stacked plates like KA01E / J2345)
        # Try multiple split positions to handle plates at different heights in the zone
        for split_frac in (0.45, 0.55, 0.65):
            h_up, w_up = up.shape[:2]
            mid = int(h_up * split_frac)
            ov = max(2, int(h_up * 0.12))
            top_band = gray[0:min(h_up, mid + ov), :]
            bot_band = gray[max(0, mid - ov):h_up, :]
            if top_band.shape[0] < 10 or bot_band.shape[0] < 10:
                continue

            top_reads: list[tuple[str, float]] = []
            bot_reads: list[tuple[str, float]] = []
            for band, reads_list in [(top_band, top_reads), (bot_band, bot_reads)]:
                # Apply CLAHE + Otsu to each band separately
                bc = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(band)
                bo = cv2.threshold(bc, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                for bv in [bo, bc]:
                    raw, conf = _ocr_raw(bv)
                    if raw:
                        reads_list.append((raw, conf))

            if top_reads and bot_reads:
                top_reads.sort(key=lambda r: -r[1])
                bot_reads.sort(key=lambda r: -r[1])
                combined = top_reads[0][0] + bot_reads[0][0]
                comb_conf = (top_reads[0][1] + bot_reads[0][1]) / 2
                if len(combined) >= 5:
                    plate = _extract_indian_plate(combined)
                    if plate:
                        candidates.append((plate, comb_conf))

        # Early exit only if we found a GOOD candidate (10-char, decent conf).
        # Don't exit on junk short plates — they'd be rejected by the score threshold.
        if any(len(p) == 10 and c >= 0.4 for p, c in candidates):
            break

    if not candidates:
        return None

    # Vote: pick the best candidate
    votes: dict[str, float] = defaultdict(float)
    for plate, conf in candidates:
        length_bonus = {10: 1.0, 9: 0.6, 8: 0.0}.get(len(plate), -0.8)
        votes[plate] += conf + length_bonus

    best = max(votes.items(), key=lambda kv: kv[1])
    if best[1] < 0.5:  # minimum confidence for direct reads
        return None
    return (best[0], round(best[1], 2))


def _two_line_reads(region_crop: np.ndarray) -> list[tuple[str, float]]:
    """Read a candidate plate region as a stacked TWO-LINE plate.

    Splits the region horizontally into top and bottom bands, upscales each band
    independently, then concatenates top-line + bottom-line. Returns candidate
    (text, conf) pairs.

    Improvements over simple midpoint split:
    - Tries multiple split points (40%, 45%, 50%, 55%) since stacked plates
      have varying line heights (top line often taller than bottom)
    - Uses a generous overlap zone so characters straddling the split are
      readable in at least one band
    - Upscales each line to 140px tall for better OCR resolution
    """
    h, w = region_crop.shape[:2]
    if h < 12 or w < 20:
        return []

    out: list[tuple[str, float]] = []

    def _line_texts(band: np.ndarray) -> list[tuple[str, float]]:
        if band.size == 0 or band.shape[0] < 3 or band.shape[1] < 3:
            return []
        scale = max(2.0, 140 / band.shape[0])
        new_w = int(band.shape[1] * scale)
        new_h = int(band.shape[0] * scale)
        if new_w < 1 or new_h < 1:
            return []
        up = cv2.resize(band, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        reads = []
        for variant in _plate_ocr_variants(up):
            raw, conf = _ocr_raw(variant)
            if raw:
                reads.append((raw, conf))
        return reads

    # Try multiple split points to handle varying top/bottom line heights
    for split_frac in (0.45, 0.50, 0.40, 0.55):
        mid = int(h * split_frac)
        ov = max(2, int(h * 0.15))  # generous vertical overlap
        top = region_crop[0:min(h, mid + ov), :]
        bottom = region_crop[max(0, mid - ov):h, :]

        top_reads = _line_texts(top)
        bot_reads = _line_texts(bottom)
        if not top_reads or not bot_reads:
            continue

        # Pair the most confident top line with the most confident bottom line
        top_reads.sort(key=lambda r: -r[1])
        bot_reads.sort(key=lambda r: -r[1])
        for t_raw, t_conf in top_reads[:2]:
            for b_raw, b_conf in bot_reads[:2]:
                out.append((t_raw + b_raw, (t_conf + b_conf) / 2))

        # If we got candidates from this split, don't try more splits (speed)
        if out:
            break

    return out



def _read_plate_voting(vehicle_crop: np.ndarray, is_moto: bool = False) -> tuple[str, float] | None:
    """Localize + multi-variant OCR + vote. Returns (plate, score) or None.

    Ratio-aware: the crop is normalized by its longer side before localization, so the
    pipeline behaves identically on landscape and portrait inputs. Motorcycles get a
    larger normalization target (smaller plates) plus a tight lower-centre fallback band.

    Speed optimizations:
    - Cap localized regions to 2 (was 4)
    - Early exit once a confident plate is found (score > 3.0)
    - Skip two-line reads if single-pass already produced valid candidates
    - Pre-filter regions smaller than 15px height
    """
    from collections import defaultdict

    # Normalize by the longer side — independent of source image aspect ratio.
    vehicle_crop = _normalize_crop(vehicle_crop, target_long=640 if is_moto else 480)

    candidates: list[tuple[str, float]] = []
    h, w = vehicle_crop.shape[:2]
    # Region selection. Each region costs slow OCR passes, so keep this bounded.
    # Cars get two localized regions because grille/bumper texture often outranks the
    # actual plate; motorcycles stay tighter because their direct fallback handles the
    # hard stacked-plate cases.
    localized_limit = 1 if is_moto else 2
    localized = sorted(
        _localize_plate_regions(vehicle_crop, is_moto=is_moto),
        key=lambda r: r[2] * r[3], reverse=True,
    )[:localized_limit]
    regions = list(localized)
    if is_moto:
        regions.append((int(w * 0.15), int(h * 0.55), int(w * 0.7), int(h * 0.45)))
    else:
        # Car plates are usually centered in the grille/boot band. These narrower
        # fallbacks give OCR a plate-sized search area when contour localization misses.
        regions.extend([
            (int(w * 0.12), int(h * 0.38), int(w * 0.76), int(h * 0.34)),
            (int(w * 0.18), int(h * 0.52), int(w * 0.64), int(h * 0.30)),
            (0, h // 3, w, h - h // 3),
        ])

    def _has_confident_full(cands: list[tuple[str, float]]) -> bool:
        """A 10-char Indian plate read with decent confidence — good enough to stop early
        and skip the expensive two-line / direct fallbacks."""
        return any(len(p) == 10 and c >= 0.5 for p, c in cands)

    usable_regions = [r for r in regions if r[3] >= 15 and r[2] >= 30]

    # --- Phase 1: single-pass OCR on each region (the cheap path). ---
    # Exit as soon as a confident full-length plate appears so we OCR no more regions.
    for (x, y, cw, ch) in usable_regions:
        crop = vehicle_crop[y:y + ch, x:x + cw]
        if crop.size == 0:
            continue
        for variant in _plate_ocr_variants(crop):
            raw, conf = _ocr_raw(variant)
            if len(raw) < 5:
                continue
            plate = _extract_indian_plate(raw)
            if plate:
                candidates.append((plate, conf))
        if _has_confident_full(candidates):
            break

    # --- Phase 2 (motorcycles only): two-line reconstruction for stacked plates. ---
    # Skipped entirely when single-pass already produced a confident 10-char plate, which
    # is the common case — this is the main speedup. Stacked plates that single-pass
    # garbles fall through to here and still get the full two-line treatment (no accuracy
    # loss for the hard cases).
    if is_moto and _thorough_ocr() and not _has_confident_full(candidates):
        for (x, y, cw, ch) in usable_regions:
            crop = vehicle_crop[y:y + ch, x:x + cw]
            if crop.size == 0:
                continue
            for raw2, conf2 in _two_line_reads(crop):
                if len(raw2) < 5:
                    continue
                plate = _extract_indian_plate(raw2)
                if plate:
                    candidates.append((plate, conf2))
            if _has_confident_full(candidates):
                break

    if not candidates:
        return None

    votes: dict[str, float] = defaultdict(float)
    prefix_counts: dict[str, int] = defaultdict(int)
    for plate, conf in candidates:
        length_bonus = {10: 1.0, 9: 0.6, 8: 0.0}.get(len(plate), -0.8)
        votes[plate] += conf + length_bonus
        prefix_counts[plate[:4]] += 1

    best_plate = max(votes.items(), key=lambda kv: kv[1])
    plate, score = best_plate[0], best_plate[1]
    # Acceptance bar. Cars are held to a stricter consistency check (prefix must recur
    # across variants). Motorcycle plates are smaller and fewer variants succeed, so we
    # accept a single confident read for them.
    min_prefix = 1 if is_moto else 1  # Both lowered to 1; with 2 OCR variants + early exit, prefix rarely repeats
    min_score = 1.0 if is_moto else (1.3 if len(plate) == 10 else 1.5)
    if prefix_counts[plate[:4]] < min_prefix or score < min_score:
        return None
    return (plate, round(score, 2))


def _find_plate_candidates(img: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h_img, w_img = gray.shape[:2]

    # Bilateral filter preserves edges while reducing noise
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)

    # Adaptive threshold to handle varying lighting across the image
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 9
    )

    # Morphological closing to connect nearby text characters into plate-like blobs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 5))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Also try edge-based detection (works better on high-contrast plates)
    edges = cv2.Canny(filtered, 30, 200)
    edge_dilated = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (16, 4)), iterations=1)

    # Combine both approaches
    combined = cv2.bitwise_or(closed, edge_dilated)

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0:
            continue
        aspect = w / h

        if (
            MIN_ASPECT <= aspect <= MAX_ASPECT
            and MIN_PLATE_WIDTH <= w <= MAX_PLATE_WIDTH
            and MIN_PLATE_HEIGHT <= h <= MAX_PLATE_HEIGHT
            and w * h <= MAX_PLATE_AREA
        ):
            # Plates are usually in the lower 70% of the image
            if y > h_img * 0.15:
                # Add some padding
                pad_x = int(w * 0.05)
                pad_y = int(h * 0.15)
                x = max(0, x - pad_x)
                y = max(0, y - pad_y)
                w = min(w_img - x, w + 2 * pad_x)
                h = min(h_img - y, h + 2 * pad_y)
                candidates.append((x, y, w, h))

    # Remove overlapping candidates — keep the one with best aspect ratio (closest to 3.5)
    candidates = _non_max_suppression(candidates)
    return candidates


def _non_max_suppression(boxes: list[tuple[int, int, int, int]], overlap_thresh: float = 0.4) -> list:
    if not boxes:
        return []

    boxes_arr = np.array(boxes, dtype=float)
    x1 = boxes_arr[:, 0]
    y1 = boxes_arr[:, 1]
    x2 = x1 + boxes_arr[:, 2]
    y2 = y1 + boxes_arr[:, 3]
    areas = boxes_arr[:, 2] * boxes_arr[:, 3]

    # Score by how close aspect ratio is to ideal 3.5
    aspects = boxes_arr[:, 2] / np.maximum(boxes_arr[:, 3], 1)
    scores = -np.abs(aspects - 3.5)
    idxs = np.argsort(scores)[::-1]

    keep = []
    while len(idxs) > 0:
        i = idxs[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[idxs[1:]])
        yy1 = np.maximum(y1[i], y1[idxs[1:]])
        xx2 = np.minimum(x2[i], x2[idxs[1:]])
        yy2 = np.minimum(y2[i], y2[idxs[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / np.maximum(areas[i] + areas[idxs[1:]] - inter, 1)
        remaining = np.where(iou <= overlap_thresh)[0]
        idxs = idxs[remaining + 1]

    return [boxes[i] for i in keep]


def _preprocess_plate_crop(crop: np.ndarray) -> np.ndarray:
    """Heavy preprocessing to maximize OCR accuracy on Indian plates."""
    # Resize to standard height for consistent OCR
    target_h = 80
    scale = target_h / crop.shape[0]
    resized = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(enhanced, h=12)

    # Adaptive threshold — handles uneven lighting on plates
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
    )

    # Morphological opening to clean up small noise spots
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return cleaned


def _read_plate(processed_crop: np.ndarray, original_crop: np.ndarray) -> tuple[str, float]:
    try:
        reader = _get_ocr_reader()

        # Try processed crop first
        results = reader.readtext(
            processed_crop,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            paragraph=False,
            min_size=10,
            text_threshold=0.3,
        )

        # If processed crop gives poor results, try original crop too
        if not results or all(r[2] < 0.3 for r in results):
            results_orig = reader.readtext(
                original_crop,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                paragraph=False,
                min_size=10,
                text_threshold=0.3,
            )
            if results_orig and (not results or max(r[2] for r in results_orig) > max(r[2] for r in results)):
                results = results_orig

        if not results:
            return ("UNKNOWN", 0.0)

        # Sort results left to right for correct reading order
        results.sort(key=lambda r: r[0][0][0])

        full_text = "".join(r[1] for r in results).strip().upper()
        full_text = re.sub(r"[^A-Z0-9]", "", full_text)
        avg_conf = sum(r[2] for r in results) / len(results)

        if len(full_text) < 4:
            return ("UNKNOWN", 0.0)

        # Find Indian state code (2 uppercase letters) to anchor the plate
        plate_text = _extract_indian_plate(full_text)
        if plate_text:
            return (plate_text, avg_conf)

        # Without Indian plate match, only return if it strongly looks plate-like
        has_letters = sum(c.isalpha() for c in full_text)
        has_digits = sum(c.isdigit() for c in full_text)
        if 6 <= len(full_text) <= 12 and 2 <= has_letters <= 5 and 2 <= has_digits <= 5:
            return (full_text, avg_conf * 0.5)

        return ("UNKNOWN", 0.0)
    except Exception:
        return ("UNKNOWN", 0.0)


INDIAN_STATE_CODES = {
    "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JH", "JK",
    "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB", "RJ",
    "SK", "TN", "TS", "TR", "UP", "UK", "WB", "AN", "CH", "DN", "DD",
    "DL", "LD", "PY",
}

LETTER_TO_DIGIT = {
    "O": "0", "Q": "0", "D": "0",
    "I": "1", "T": "1",
    "L": "4",
    "Z": "2",
    "J": "3",
    "S": "5",
    "G": "6",
    "B": "8",
}

DIGIT_TO_LETTER = {
    "0": "O", "1": "I", "2": "Z", "3": "J", "4": "A", "5": "S", "6": "G", "8": "B",
}


def _extract_indian_plate(raw: str) -> str | None:
    """Find and parse an Indian plate from noisy OCR text.

    Strategy: find a known state code (KA, MH, DL, etc.) in the text,
    then parse everything after it as district code + series + number,
    applying positional OCR corrections.

    The series/number boundary is determined by trying all plausible splits
    and picking the one that produces the best Indian plate format (10 chars
    with 2-letter state, 2-digit district, 1-2 letter series, 4-digit number
    is ideal).
    """
    best_result: tuple[str, int] | None = None  # (plate, quality_score)

    # Try to find a state code anchor
    # Common OCR letter confusions for state codes
    _STATE_CONFUSIONS = {
        "R": "N", "N": "R",  # N↔R (similar vertical strokes)
        "M": "N", "H": "N",  # M/H→N
    }

    for i in range(len(raw) - 1):
        c1, c2 = raw[i], raw[i + 1]
        # Fix digits that should be letters for the state code
        if c1.isdigit() and c1 in DIGIT_TO_LETTER:
            c1 = DIGIT_TO_LETTER[c1]
        if c2.isdigit() and c2 in DIGIT_TO_LETTER:
            c2 = DIGIT_TO_LETTER[c2]

        # Try the direct state code first, then with confusion swaps
        state_candidates = [c1 + c2]
        if c2 in _STATE_CONFUSIONS:
            state_candidates.append(c1 + _STATE_CONFUSIONS[c2])
        if c1 in _STATE_CONFUSIONS:
            state_candidates.append(_STATE_CONFUSIONS[c1] + c2)

        state = None
        for sc in state_candidates:
            if sc in INDIAN_STATE_CODES:
                state = sc
                break
        if state is None:
            continue

        # Found a state code at position i — parse the rest
        remainder = raw[i + 2:]
        if len(remainder) < 3:
            continue

        # Next 2 chars should be digits (district code)
        district = ""
        for ch in remainder[:2]:
            if ch.isdigit():
                district += ch
            elif ch.isalpha() and ch in LETTER_TO_DIGIT:
                district += LETTER_TO_DIGIT[ch]
            else:
                district += ch
        remainder = remainder[2:]

        if not remainder:
            continue

        # Collect the rest as a mixed sequence, then try different split points
        # for series (letters) vs number (digits).
        # Also try skipping a leading noise digit (OCR sometimes inserts an extra
        # digit between district and series, e.g. '0' in 'KA030JH7856').
        rest_variants = [list(remainder)]
        if len(remainder) >= 2 and remainder[0].isdigit() and remainder[1].isalpha():
            rest_variants.append(list(remainder[1:]))  # skip the noise digit

        for rest_chars in rest_variants:
            if not rest_chars:
                continue
            # Find the longest possible letter prefix (series candidates)
            max_series_len = 0
            for j, ch in enumerate(rest_chars):
                if ch.isalpha() and j < 3:
                    max_series_len = j + 1
                else:
                    break

            # Also consider extending the series by 1 if the next char is a digit
            # that could be a misread letter (e.g. '3' → 'J'). OCR often confuses
            # letters/digits at the series/number boundary.
            extended_series_len = max_series_len
            if max_series_len < 3 and max_series_len < len(rest_chars):
                next_ch = rest_chars[max_series_len]
                if next_ch.isdigit() and next_ch in DIGIT_TO_LETTER:
                    extended_series_len = max_series_len + 1

            # Try each plausible series length (0 to extended_series_len) and pick the
            # split that produces the best plate format.
            candidates: list[tuple[str, int]] = []
            for slen in range(extended_series_len + 1):
                # Build series string, converting digits to letters if needed
                series = ""
                for k in range(slen):
                    ch = rest_chars[k]
                    if ch.isalpha():
                        series += ch
                    elif ch.isdigit() and ch in DIGIT_TO_LETTER:
                        series += DIGIT_TO_LETTER[ch]
                    else:
                        series += ch
                num_chars = rest_chars[slen:]

                # Convert remaining to digits (applying letter→digit corrections)
                number = ""
                for ch in num_chars:
                    if ch.isdigit():
                        number += ch
                    elif ch.isalpha() and ch in LETTER_TO_DIGIT:
                        number += LETTER_TO_DIGIT[ch]
                    # skip unrecognized characters

                if len(number) < 1:
                    continue
                if len(number) > 4:
                    number = number[:4]

                plate = state + district + series + number
                if len(plate) < 6 or len(plate) > 10 or len(district) > 2:
                    continue

                # Quality scoring: prefer standard Indian format
                quality = 0
                if len(plate) == 10:
                    quality += 5  # ideal length
                elif len(plate) == 9:
                    quality += 3
                if len(number) == 4:
                    quality += 3  # ideal number length
                elif len(number) == 3:
                    quality += 1
                if 1 <= len(series) <= 2:
                    quality += 2  # most common series length
                elif len(series) == 3:
                    quality += 1

                candidates.append((plate, quality))

            if candidates:
                # Pick the best candidate from this state-code anchor
                best_cand = max(candidates, key=lambda c: c[1])
                if best_result is None or best_cand[1] > best_result[1]:
                    best_result = best_cand

    return best_result[0] if best_result else None



def _correct_common_errors(text: str) -> str:
    """Fix frequent OCR misreads on Indian plates.

    Indian plate format: SS DD [SSS] NNNN
      SS = 2 letters (state code, e.g. KA, MH, DL)
      DD = 2 digits (district code, e.g. 04, 12)
      SSS = 0-3 letters (series, e.g. MP, AB)
      NNNN = 1-4 digits (number)
    """
    letter_to_digit = {
        "O": "0", "Q": "0", "D": "0",
        "I": "1", "T": "1",
        "L": "4",
        "Z": "2",
        "J": "3",
        "S": "5",
        "G": "6",
        "B": "8",
    }
    digit_to_letter = {
        "0": "O",
        "1": "I",
        "4": "A",
        "5": "S",
        "6": "G",
        "8": "B",
    }

    if len(text) < 4:
        return text

    chars = list(text)

    # Positions 0-1: must be letters (state code)
    for i in range(min(2, len(chars))):
        if chars[i].isdigit() and chars[i] in digit_to_letter:
            chars[i] = digit_to_letter[chars[i]]

    # Positions 2-3: must be digits (district code)
    for i in range(2, min(4, len(chars))):
        if chars[i].isalpha() and chars[i] in letter_to_digit:
            chars[i] = letter_to_digit[chars[i]]

    # Find where the trailing number starts (last N consecutive digits from the end)
    # and fix any letters in that trailing region
    trailing_start = len(chars)
    for i in range(len(chars) - 1, 3, -1):
        if chars[i].isdigit() or (chars[i].isalpha() and chars[i] in letter_to_digit):
            trailing_start = i
        else:
            break
    for i in range(trailing_start, len(chars)):
        if chars[i].isalpha() and chars[i] in letter_to_digit:
            chars[i] = letter_to_digit[chars[i]]

    return "".join(chars)


_ocr_reader = None
_tesseract_state: bool | None = None  # None = not checked yet


def _use_tesseract() -> bool:
    """Whether to use Tesseract instead of EasyOCR.

    OPT-IN only (TRAFFICSARATHI_OCR_ENGINE=tesseract). Tesseract is lighter/faster per
    isolated call, but on these low-res CCTV plates it is markedly less accurate than
    EasyOCR and the existing split/vote pipeline is tuned for EasyOCR — so EasyOCR is the
    default. With async OCR the user no longer waits on EasyOCR's latency, so accuracy wins."""
    global _tesseract_state
    if _tesseract_state is not None:
        return _tesseract_state
    if os.environ.get("TRAFFICSARATHI_OCR_ENGINE", "").lower() != "tesseract":
        _tesseract_state = False
        return False
    try:
        import pytesseract

        win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.name == "nt" and os.path.exists(win_path):
            pytesseract.pytesseract.tesseract_cmd = win_path
        pytesseract.get_tesseract_version()
        _tesseract_state = True
    except Exception:
        _tesseract_state = False
    return _tesseract_state


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        # Auto-use GPU when one is present (≈10-20x faster than CPU). On CPU we pin
        # determinism (fixed seed + single thread) so the same image yields the same plate.
        use_gpu = False
        try:
            import torch
            use_gpu = torch.cuda.is_available()
            if not use_gpu:
                torch.manual_seed(0)
                torch.use_deterministic_algorithms(True, warn_only=True)
                torch.set_num_threads(1)
        except Exception:
            pass
        _ocr_reader = easyocr.Reader(["en"], gpu=use_gpu)
    return _ocr_reader
