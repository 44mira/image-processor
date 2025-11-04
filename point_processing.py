"""
Implements various point cloud processing functions including:
1. Grayscale transformation
2. Negative transformation
3. Black/White via manual thresholding
4. Power-law (Gamma) transformation
5. Histogram equalization

For methods (3) and (4), allow the user to select a threshold value
from range [0, 255] and gamma (γ) values, respectively.
"""

import numpy as np
from PyQt6.QtGui import QImage


def qimage_to_ndarray(qimage: QImage) -> np.ndarray:
    """Convert QImage to NumPy ndarray (RGB) safely handling padded rows."""
    qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
    width, height = qimage.width(), qimage.height()
    bytes_per_line = qimage.bytesPerLine()

    ptr = qimage.bits()
    ptr.setsize(height * bytes_per_line)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))

    # Extract only the RGB part (3 bytes per pixel)
    arr = arr[:, : width * 3]  # drop padding bytes
    arr = arr.reshape((height, width, 3))

    return arr.copy()  # detach from Qt buffer to prevent corruption


def ndarray_to_qimage(arr: np.ndarray) -> QImage:
    """Convert NumPy ndarray (RGB or grayscale) back to QImage."""
    if arr.ndim == 2:  # grayscale
        h, w = arr.shape
        qimg = QImage(arr.data, w, h, w, QImage.Format.Format_Grayscale8)
    elif arr.ndim == 3 and arr.shape[2] == 3:  # RGB
        h, w, _ = arr.shape
        qimg = QImage(arr.data, w, h, w * 3, QImage.Format.Format_RGB888)
    else:
        raise ValueError(f"Unsupported array shape: {arr.shape}")

    return qimg.copy()  # return deep copy to avoid referencing numpy buffer


def to_grayscale(rgb_points: np.ndarray) -> np.ndarray:
    """Convert RGB point cloud to grayscale using luminosity method."""

    if rgb_points.ndim not in (2, 3) or rgb_points.shape[-1] != 3:
        raise ValueError("Input must be an array with 3 channels (RGB).")

    # standard luminance coefficients for RGB to grayscale (Rec. 601)
    RED_WEIGHT = 0.2989
    GREEN_WEIGHT = 0.5870
    BLUE_WEIGHT = 0.1140

    # Apply weighted sum to get grayscale intensity
    grayscale = (
        RED_WEIGHT * rgb_points[..., 0]
        + GREEN_WEIGHT * rgb_points[..., 1]
        + BLUE_WEIGHT * rgb_points[..., 2]
    )

    return grayscale.astype(np.uint8)
