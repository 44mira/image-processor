import cv2
import numpy as np


def averaging_filter(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Apply an averaging (mean) filter."""
    return cv2.blur(image, (ksize, ksize))


def median_filter(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Apply a median filter."""
    return cv2.medianBlur(image, ksize)


def laplacian_highpass(image: np.ndarray) -> np.ndarray:
    """Apply highpass filtering using a Laplacian operator."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    laplacian = cv2.convertScaleAbs(laplacian)
    return laplacian


def unsharp_mask(
    image: np.ndarray, ksize: int = 5, amount: float = 1.0
) -> np.ndarray:
    """Apply unsharp masking for sharpening."""
    blurred = cv2.GaussianBlur(image, (ksize, ksize), 0)
    sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
    return sharpened
