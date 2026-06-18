import cv2
import numpy as np


def _is_low_light(img: np.ndarray, threshold: float = 60.0) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)) < threshold


def _is_blurry(img: np.ndarray, threshold: float = 80.0) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var() < threshold


def _is_rainy(img: np.ndarray) -> bool:
    """Detect rain by looking for high-frequency vertical streaks.

    Rain appears as thin, bright, near-vertical lines across the image.  We
    check if the vertical Sobel response dominates the horizontal one — a sign
    of rain streaks overlaid on the scene.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobel_v = np.mean(np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)))
    sobel_h = np.mean(np.abs(cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)))
    # Vertical energy significantly higher than horizontal → rain streaks
    return sobel_v > sobel_h * 1.4 and sobel_v > 15


def _has_strong_shadows(img: np.ndarray) -> bool:
    """Detect strong shadows: large dark regions with sharp brightness boundaries.

    Shadows manifest as bimodal brightness distribution in the L channel.  We
    check if the standard-deviation is high relative to the mean — indicating
    a wide spread between shadowed and sunlit areas.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0].astype(float)
    mean_l = np.mean(l_channel)
    std_l = np.std(l_channel)
    # High relative std = large contrast between shadow and non-shadow
    return std_l > 45 and mean_l < 160


def _has_motion_blur(img: np.ndarray) -> bool:
    """Detect motion blur via Fourier spectrum analysis.

    Motion blur concentrates energy along the blur direction in the frequency
    domain, creating a "streak" through the centre.  A simple proxy: compare
    the Laplacian variance (sharpness) to an expected floor; very low values
    with moderate brightness suggest motion blur rather than just low light.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_brightness = float(np.mean(gray))
    # Low sharpness + reasonable brightness → motion blur (not just dark scene)
    return lap_var < 40 and mean_brightness > 50


def _apply_clahe(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def _unsharp_mask(img: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1.5, blurred, -0.5, 0)


def _auto_white_balance(img: np.ndarray) -> np.ndarray:
    result = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    avg_a = np.mean(result[:, :, 1])
    avg_b = np.mean(result[:, :, 2])
    result[:, :, 1] = np.clip(result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1), 0, 255).astype(np.uint8)
    result[:, :, 2] = np.clip(result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1), 0, 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)


def _remove_rain(img: np.ndarray) -> np.ndarray:
    """Suppress rain streaks using a guided median filter.

    Median filter removes the thin bright streaks (rain) while preserving
    edges better than Gaussian blur.  We apply it only on the luminance
    channel to avoid colour bleeding.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    # ksize=5 is enough to suppress 1-3px wide rain streaks
    l = cv2.medianBlur(l, 5)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def _remove_shadows(img: np.ndarray) -> np.ndarray:
    """Reduce shadow intensity by equalizing the L channel in dark regions.

    We dilate the image to estimate the background illumination, then divide
    the original L channel by it — effectively normalizing the brightness
    across shadowed and sunlit regions.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    # Estimate background illumination with a large dilation
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    bg = cv2.dilate(l, kernel)
    bg = cv2.medianBlur(bg, 31)
    # Normalize: scale L so that shadowed areas are lifted
    bg_float = bg.astype(np.float32)
    bg_float[bg_float == 0] = 1  # avoid division by zero
    normalized = (l.astype(np.float32) * 180.0 / bg_float)
    l_out = np.clip(normalized, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([l_out, a, b]), cv2.COLOR_LAB2BGR)


def _correct_motion_blur(img: np.ndarray) -> np.ndarray:
    """Apply a stronger unsharp mask to counter motion blur.

    Full Wiener deconvolution requires knowing the blur kernel direction and
    length — impractical for a general pipeline.  Instead we use a more
    aggressive unsharp mask (higher weight, larger kernel) which partially
    recovers edge detail lost to moderate motion blur.
    """
    blurred = cv2.GaussianBlur(img, (0, 0), 5)
    return cv2.addWeighted(img, 2.0, blurred, -1.0, 0)


def preprocess(img: np.ndarray) -> np.ndarray:
    img = _auto_white_balance(img)
    if _is_low_light(img):
        img = _apply_clahe(img)
    if _is_rainy(img):
        img = _remove_rain(img)
    if _has_strong_shadows(img):
        img = _remove_shadows(img)
    if _has_motion_blur(img):
        img = _correct_motion_blur(img)
    elif _is_blurry(img):
        img = _unsharp_mask(img)
    return img

