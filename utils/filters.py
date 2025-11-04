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


def convolve2d(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Perform 2D convolution on a single-channel image (grayscale)."""
    kh, kw = kernel.shape
    pad_y, pad_x = kh // 2, kw // 2

    # Pad the image to handle borders
    padded = np.pad(image, ((pad_y, pad_y), (pad_x, pad_x)), mode="reflect")
    output = np.zeros_like(image, dtype=float)

    # Flip kernel (for convolution)
    kernel_flipped = np.flipud(np.fliplr(kernel))

    # Convolve
    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            region = padded[y : y + kh, x : x + kw]
            output[y, x] = np.sum(region * kernel_flipped)

    return output
