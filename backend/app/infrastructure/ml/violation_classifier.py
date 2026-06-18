from abc import ABC, abstractmethod

import numpy as np

from app.domain.entities import BoundingBox, DetectedObject, ViolationResult
from app.domain.enums import Severity, VehicleCategory, ViolationType, VIOLATION_SEVERITY_MAP


class ViolationDetector(ABC):
    @abstractmethod
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        ...


def _iou(a: BoundingBox, b: BoundingBox) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.w, b.x + b.w)
    y2 = min(a.y + a.h, b.y + b.h)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def _overlap_ratio(person: BoundingBox, vehicle: BoundingBox) -> float:
    x1 = max(person.x, vehicle.x)
    y1 = max(person.y, vehicle.y)
    x2 = min(person.x + person.w, vehicle.x + vehicle.w)
    y2 = min(person.y + person.h, vehicle.y + vehicle.h)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    person_area = person.w * person.h
    return inter / person_area if person_area > 0 else 0.0


class HelmetViolationDetector(ViolationDetector):
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        violations = []
        motorcycles = [o for o in objects if o.category == VehicleCategory.MOTORCYCLE]
        persons = [o for o in objects if o.label == "person"]

        for moto in motorcycles:
            # A helmet violation requires a person actually MOUNTED on the bike — their
            # bbox must overlap the motorcycle. The loose proximity test (used for
            # triple-riding) wrongly associates a pedestrian standing NEXT to a parked
            # bike, producing a false helmet violation on a rider-less (parked) bike.
            riders = [p for p in persons if _overlap_ratio(p.bbox, moto.bbox) > 0.15]
            for rider in riders:
                head_region = BoundingBox(
                    x=rider.bbox.x,
                    y=rider.bbox.y,
                    w=rider.bbox.w,
                    h=rider.bbox.h // 3,
                )
                h_y = head_region.y
                h_h = head_region.h
                head_crop = image[h_y : h_y + h_h, head_region.x : head_region.x + head_region.w]

                if head_crop.size == 0:
                    continue

                has_helmet = self._check_helmet(head_crop)
                if not has_helmet:
                    violations.append(
                        ViolationResult(
                            violation_type=ViolationType.HELMET,
                            severity=VIOLATION_SEVERITY_MAP[ViolationType.HELMET],
                            confidence=round(moto.confidence * 0.85, 3),
                            bbox=rider.bbox,
                            vehicle_category=VehicleCategory.MOTORCYCLE,
                            vehicle_bbox=moto.bbox,
                        )
                    )
        return violations

    def _check_helmet(self, head_crop: np.ndarray) -> bool:
        try:
            from app.infrastructure.ml.model_registry import get_model

            model = get_model("helmet_detector")
            results = model(head_crop, conf=0.4, verbose=False)
            for r in results:
                for box in r.boxes:
                    cls_name = r.names[int(box.cls[0])]
                    if "helmet" in cls_name.lower():
                        return True
        except Exception:
            pass
        return False


class TripleRidingDetector(ViolationDetector):
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        violations = []
        motorcycles = [o for o in objects if o.category == VehicleCategory.MOTORCYCLE]
        persons = [o for o in objects if o.label == "person"]

        for moto in motorcycles:
            riders = [p for p in persons if self._is_rider(p.bbox, moto.bbox)]
            if len(riders) >= 3:
                violations.append(
                    ViolationResult(
                        violation_type=ViolationType.TRIPLE_RIDING,
                        severity=VIOLATION_SEVERITY_MAP[ViolationType.TRIPLE_RIDING],
                        confidence=round(moto.confidence * 0.9, 3),
                        bbox=moto.bbox,
                        vehicle_category=VehicleCategory.MOTORCYCLE,
                        vehicle_bbox=moto.bbox,
                    )
                )
        return violations

    @staticmethod
    def _is_rider(person: BoundingBox, moto: BoundingBox) -> bool:
        if _overlap_ratio(person, moto) > 0.15:
            return True
        p_cx = person.x + person.w / 2
        p_bottom = person.y + person.h
        m_left = moto.x - moto.w * 0.3
        m_right = moto.x + moto.w * 1.3
        m_top = moto.y - moto.h * 1.5
        m_bottom = moto.y + moto.h
        if m_left <= p_cx <= m_right and m_top <= p_bottom <= m_bottom:
            return True
        return False


class SeatbeltDetector(ViolationDetector):
    """Seatbelt violation via front-windshield analysis — PRECISION-FIRST.

    A seatbelt strap is only physically observable when the car's cabin faces the
    camera AND the cabin is resolved at enough pixels to see the diagonal strap.
    Rear-view CCTV (our sample images image2/image3) shows only the back of the car,
    so seatbelt status is unknowable — asserting a violation there would be a false
    positive. We therefore GATE detection on two hard conditions:

      1. The car is FRONT-FACING (headlights/windshield toward camera), reusing the
         same orientation classifier as wrong-side detection.
      2. The car is large enough in frame (close) that the windshield is resolvable.

    Only when both hold, and an occupant is visible but no diagonal strap is found,
    do we emit a violation. On rear-view / distant footage the detector correctly
    abstains (0 false positives). Recall should be validated on close front-view
    footage where seatbelts are actually visible.
    """

    # The car must occupy at least this fraction of the frame for the cabin to be
    # resolvable enough to judge a seatbelt. Distant CCTV cars fall below this.
    MIN_CABIN_AREA_FRAC = 0.10

    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        import cv2

        violations = []
        h_img, w_img = image.shape[:2]
        frame_area = max(h_img * w_img, 1)
        cars = [o for o in objects if o.category == VehicleCategory.CAR]

        for car in cars:
            cb = car.bbox
            # Gate 1: cabin must be resolvable (close enough).
            if (cb.w * cb.h) / frame_area < self.MIN_CABIN_AREA_FRAC:
                continue
            # Gate 2: cabin must face the camera. From behind we cannot see the strap.
            if not WrongSideDetector._is_front_facing(image, cb):
                continue

            # Windshield region = upper 45% of the (front-facing) car.
            wr_y = cb.y
            wr_h = int(cb.h * 0.45)
            wr_x = cb.x + int(cb.w * 0.12)
            wr_w = int(cb.w * 0.76)
            wr_crop = image[wr_y:wr_y + wr_h, wr_x:wr_x + wr_w]
            # Require an absolute pixel floor so the strap is actually resolvable.
            if wr_crop.size == 0 or wr_crop.shape[0] < 50 or wr_crop.shape[1] < 70:
                continue

            # Confirm an occupant (driver) silhouette is present before judging.
            gray = cv2.cvtColor(wr_crop, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            has_occupant = False
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 100:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                if bh == 0:
                    continue
                ar = bw / bh
                if 0.5 <= ar <= 2.0 and area > (wr_crop.shape[0] * wr_crop.shape[1]) * 0.02:
                    has_occupant = True
                    break

            if has_occupant and not self._check_seatbelt_strap(wr_crop):
                violations.append(
                    ViolationResult(
                        violation_type=ViolationType.SEATBELT,
                        severity=VIOLATION_SEVERITY_MAP[ViolationType.SEATBELT],
                        confidence=round(car.confidence * 0.6, 3),
                        bbox=BoundingBox(x=wr_x, y=wr_y, w=wr_w, h=wr_h),
                        vehicle_category=VehicleCategory.CAR,
                        vehicle_bbox=car.bbox,
                    )
                )
        return violations

    def _check_seatbelt_strap(self, crop: np.ndarray) -> bool:
        """Look for diagonal lines consistent with a seatbelt strap."""
        import cv2

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 30, minLineLength=20, maxLineGap=5)
        if lines is not None:
            diagonal_count = 0
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                    angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                    if 20 < angle < 70:
                        diagonal_count += 1
            if diagonal_count >= 2:
                return True
        return False


class IllegalParkingDetector(ViolationDetector):
    """Single-frame illegal-parking heuristic.

    Flags vehicles positioned near the road edges (shoulders/sidewalks) which is
    a common indicator of illegal parking in Indian urban CCTV footage. Since we
    can't determine motion from a single frame, confidence is kept low. The
    detector also checks for motion-blur absence (parked vehicles are sharp) and
    boosts confidence if the vehicle is near the frame edge where sidewalks
    typically appear.
    """
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        import cv2

        violations = []
        h, w = image.shape[:2]
        vehicles = [o for o in objects if o.category in (
            VehicleCategory.CAR, VehicleCategory.MOTORCYCLE, VehicleCategory.TRUCK, VehicleCategory.BUS
        )]
        persons = [o for o in objects if o.label == "person"]

        # Edge zones: leftmost and rightmost 20% of the frame (typical sidewalk/shoulder)
        left_boundary = int(w * 0.20)
        right_boundary = int(w * 0.80)

        for v in vehicles:
            in_edge_zone = v.bbox.x <= left_boundary or (v.bbox.x + v.bbox.w) >= right_boundary
            v_cx = v.bbox.x + v.bbox.w / 2

            # A motorcycle with NOBODY mounted on it is, in a still frame, a parked bike —
            # flag it as illegal parking even when it's not in the edge zone (moving bikes
            # almost always have a detected rider). This implements the "no human on the
            # vehicle → parked" rule and is what keeps a rider-less bike from being missed.
            is_riderless_moto = (
                v.category == VehicleCategory.MOTORCYCLE
                and not any(_overlap_ratio(p.bbox, v.bbox) > 0.15 for p in persons)
            )

            if not in_edge_zone and not is_riderless_moto:
                continue

            # Skip very small detections (distant vehicles)
            if v.bbox.w * v.bbox.h < (w * h) * 0.005:
                continue

            # Check for motion blur — parked vehicles are typically sharp
            crop = image[v.bbox.y:v.bbox.y + v.bbox.h, v.bbox.x:v.bbox.x + v.bbox.w]
            if crop.size == 0:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

            # High blur score = sharp image = likely stationary
            if blur_score < 50:  # too blurry, probably moving
                continue

            # Base confidence is low for single-frame
            conf = 0.48
            if is_riderless_moto:
                conf += 0.08  # a bike with no rider is a strong parked signal
            # Boost if very close to edge (deep into the shoulder)
            if v_cx < int(w * 0.10) or v_cx > int(w * 0.90):
                conf += 0.07
            # Boost if vehicle is in lower half (closer to camera = more confident)
            if v.bbox.y + v.bbox.h > h * 0.5:
                conf += 0.05

            violations.append(
                ViolationResult(
                    violation_type=ViolationType.ILLEGAL_PARKING,
                    severity=VIOLATION_SEVERITY_MAP[ViolationType.ILLEGAL_PARKING],
                    confidence=round(min(conf, 0.65) * v.confidence, 3),
                    bbox=v.bbox,
                    vehicle_category=v.category,
                    vehicle_bbox=v.bbox,
                )
            )
        return violations


class WrongSideDetector(ViolationDetector):
    """Wrong-side detection via vehicle orientation analysis.

    Indian CCTV typically views traffic from behind. Vehicles moving in the
    correct direction show their rear (taillights, license plate at bottom).
    A vehicle facing the camera (headlights visible, bright spots in upper
    portion) is likely driving on the wrong side. We compare each vehicle's
    facing direction against the majority.
    """
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        import cv2

        violations = []
        h, w = image.shape[:2]
        vehicles = [o for o in objects if o.category not in (VehicleCategory.UNKNOWN, VehicleCategory.BICYCLE)]

        if len(vehicles) < 3:
            return violations

        # Classify each vehicle as front-facing or rear-facing
        orientations: list[tuple[DetectedObject, bool]] = []  # (vehicle, is_front_facing)
        for v in vehicles:
            is_front = self._is_front_facing(image, v.bbox)
            orientations.append((v, is_front))

        front_count = sum(1 for _, f in orientations if f)
        rear_count = len(orientations) - front_count

        # The minority direction is wrong-side. Need at least 3 vehicles and
        # the minority must be at most 1 (clear outlier).
        if front_count == 0 or rear_count == 0:
            return violations

        wrong_is_front = front_count < rear_count
        # Only flag if the minority is a clear outlier (<=1 vehicle)
        minority_count = front_count if wrong_is_front else rear_count
        if minority_count > 1:
            return violations

        # Same-lane guard: on a TWO-WAY road, oncoming traffic legitimately faces the
        # camera but travels on the OPPOSITE side. A genuine wrong-way driver is going
        # against the flow IN THE SAME LANE — i.e. horizontally among the majority. So we
        # only flag the outlier if its centre-x falls within the majority's horizontal
        # span. This removes the classic false positive on normal oncoming traffic.
        majority_cx = [
            v.bbox.x + v.bbox.w / 2 for v, is_front in orientations if is_front != wrong_is_front
        ]
        if not majority_cx:
            return violations
        maj_lo, maj_hi = min(majority_cx), max(majority_cx)

        for v, is_front in orientations:
            if is_front == wrong_is_front:
                v_cx = v.bbox.x + v.bbox.w / 2
                if not (maj_lo <= v_cx <= maj_hi):
                    continue  # opposite side of the road → normal oncoming traffic
                violations.append(
                    ViolationResult(
                        violation_type=ViolationType.WRONG_SIDE,
                        severity=VIOLATION_SEVERITY_MAP[ViolationType.WRONG_SIDE],
                        confidence=round(v.confidence * 0.6, 3),
                        bbox=v.bbox,
                        vehicle_category=v.category,
                        vehicle_bbox=v.bbox,
                    )
                )
        return violations

    @staticmethod
    def _is_front_facing(image: np.ndarray, bbox: BoundingBox) -> bool:
        """Determine if a vehicle is front-facing (headlights visible).

        Front-facing vehicles show headlights (bright circular spots) in their
        upper portion. Rear-facing vehicles show taillights (red spots) in
        their lower portion. We check for bright white/yellow spots in the
        upper third vs red spots in the lower third.
        """
        import cv2

        crop = image[bbox.y:bbox.y + bbox.h, bbox.x:bbox.x + bbox.w]
        if crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
            return False

        ch, cw = crop.shape[:2]
        upper = crop[0:ch // 3, :]
        lower = crop[2 * ch // 3:, :]

        # Check for bright headlights in upper region (front-facing)
        hsv_upper = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
        # Headlights: high value (bright), low-to-mid saturation
        bright_mask = cv2.inRange(hsv_upper, np.array([0, 0, 200]), np.array([180, 80, 255]))
        bright_ratio = np.count_nonzero(bright_mask) / max(bright_mask.size, 1)

        # Check for red taillights in lower region (rear-facing)
        hsv_lower = cv2.cvtColor(lower, cv2.COLOR_BGR2HSV)
        red_mask1 = cv2.inRange(hsv_lower, np.array([0, 80, 100]), np.array([10, 255, 255]))
        red_mask2 = cv2.inRange(hsv_lower, np.array([160, 80, 100]), np.array([180, 255, 255]))
        red_mask = red_mask1 | red_mask2
        red_ratio = np.count_nonzero(red_mask) / max(red_mask.size, 1)

        # Front-facing = significant bright spots in upper, less red in lower
        if bright_ratio > 0.03 and red_ratio < 0.01:
            return True
        # Rear-facing = red taillights in lower portion
        if red_ratio > 0.02:
            return False
        # Ambiguous — default to rear-facing (normal direction)
        return False


class StopLineDetector(ViolationDetector):
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        import cv2

        violations = []
        h, w = image.shape[:2]

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lower_region = gray[int(h * 0.6) :, :]
        edges = cv2.Canny(lower_region, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=w // 3, maxLineGap=20)

        if lines is None:
            return violations

        stop_line_y = None
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 10 and abs(x2 - x1) > w // 4:
                stop_line_y = int(h * 0.6) + (y1 + y2) // 2
                break

        if stop_line_y is None:
            return violations

        vehicles = [o for o in objects if o.category != VehicleCategory.UNKNOWN]
        for v in vehicles:
            v_bottom = v.bbox.y + v.bbox.h
            if v_bottom > stop_line_y:
                violations.append(
                    ViolationResult(
                        violation_type=ViolationType.STOP_LINE,
                        severity=VIOLATION_SEVERITY_MAP[ViolationType.STOP_LINE],
                        confidence=round(v.confidence * 0.65, 3),
                        bbox=v.bbox,
                        vehicle_category=v.category,
                        vehicle_bbox=v.bbox,
                    )
                )
        return violations


class RedLightDetector(ViolationDetector):
    def detect(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        import cv2

        h, w = image.shape[:2]
        upper = image[: int(h * 0.4), :]
        hsv = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

        # A real red signal is a compact, roughly circular blob — not scattered red
        # clutter (taillights, signage, clothing). Look for a traffic-light-like blob.
        signal_found = False
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 60 or area > 4000:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bh == 0:
                continue
            aspect = bw / bh
            # Traffic signal lamp is roughly square/circular
            if 0.6 <= aspect <= 1.6:
                fill = area / (bw * bh)
                if fill >= 0.6:  # solid blob, not a hollow shape
                    signal_found = True
                    break

        if not signal_found:
            return []

        violations = []
        vehicles = [o for o in objects if o.category != VehicleCategory.UNKNOWN]
        for v in vehicles:
            if v.bbox.y > h * 0.4:
                violations.append(
                    ViolationResult(
                        violation_type=ViolationType.RED_LIGHT,
                        severity=VIOLATION_SEVERITY_MAP[ViolationType.RED_LIGHT],
                        confidence=round(v.confidence * 0.55, 3),
                        bbox=v.bbox,
                        vehicle_category=v.category,
                        vehicle_bbox=v.bbox,
                    )
                )
        return violations


class ViolationPipeline:
    def __init__(self):
        self.detectors: list[ViolationDetector] = [
            HelmetViolationDetector(),
            TripleRidingDetector(),
            SeatbeltDetector(),
            IllegalParkingDetector(),
            WrongSideDetector(),
            StopLineDetector(),
            RedLightDetector(),
        ]

    def run(self, image: np.ndarray, objects: list[DetectedObject]) -> list[ViolationResult]:
        violations = []
        for detector in self.detectors:
            try:
                violations.extend(detector.detect(image, objects))
            except Exception:
                continue
        violations = [v for v in violations if v.confidence >= 0.45]
        return self._deduplicate(violations)

    @staticmethod
    def _deduplicate(violations: list[ViolationResult]) -> list[ViolationResult]:
        kept = []
        for v in sorted(violations, key=lambda x: -x.confidence):
            duplicate = False
            for k in kept:
                if k.violation_type == v.violation_type and _iou(k.bbox, v.bbox) > 0.3:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(v)
        return kept
