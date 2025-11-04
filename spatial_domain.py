import numpy as np

from point_processing import to_grayscale
from utils.filters import convolve2d


def averaging_filter(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Apply an averaging (mean) filter."""
    kernel = np.ones((ksize, ksize), dtype=float) / (ksize * ksize)
    if image.ndim == 3:  # RGB
        channels = [convolve2d(image[..., i], kernel) for i in range(3)]
        result = np.stack(channels, axis=2)
    else:
        result = convolve2d(image, kernel)

    return np.clip(result, 0, 255).astype(np.uint8)


def median_filter(image: np.ndarray, ksize: int = 3) -> np.ndarray:
    """Apply a median filter."""
    pad = ksize // 2
    if image.ndim == 3:  # RGB
        channels = [median_filter(image[..., i], ksize) for i in range(3)]
        return np.stack(channels, axis=2)

    padded = np.pad(image, pad, mode="reflect")
    output = np.zeros_like(image)

    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            region = padded[y : y + ksize, x : x + ksize]
            output[y, x] = np.median(region)

    return output.astype(np.uint8)


def laplacian_highpass(image: np.ndarray) -> np.ndarray:
    """Apply highpass filtering using a Laplacian operator."""
    laplacian_kernel = np.array(
        [[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=float
    )

    # standard luminance coefficients for RGB to grayscale (Rec. 601)
    RED_WEIGHT = 0.2989
    GREEN_WEIGHT = 0.5870
    BLUE_WEIGHT = 0.1140

    if image.ndim == 3:  # RGB
        gray = (
            RED_WEIGHT * image[..., 0]
            + GREEN_WEIGHT * image[..., 1]
            + BLUE_WEIGHT * image[..., 2]
        ).astype(np.uint8)
    else:
        gray = image

    result = convolve2d(gray, laplacian_kernel)
    result = np.abs(result)  # take magnitude
    result = (result / result.max()) * 255  # normalize for display
    return result.astype(np.uint8)


# equivalent
# def laplacian_highpass(image: np.ndarray) -> np.ndarray:
#     """Apply highpass filtering using a Laplacian operator."""
#     laplacian = cv2.Laplacian(image, cv2.CV_64F, ksize=3)
#     laplacian = cv2.convertScaleAbs(laplacian)
#     return laplacian


def unsharp_mask(image: np.ndarray, k: float = 1.0) -> np.ndarray:
    """
    Unsharp Mask occurs when `k` = 1, Highboost filter when `k` > 1.

    Args:
        image: The image to apply the filter to
        k: Sharpening multiplier
    """

    if image.ndim == 3:
        image = to_grayscale(image)

    # apply blurring filter
    blur_kernel = np.ones((3, 3), dtype=float) / 9.0
    blurred = convolve2d(image, blur_kernel)

    # subtract blur mask from grayscaled
    mask = image - blurred

    # add the mask back into the original image
    sharpened = image + k * mask

    sharpened = np.clip(sharpened, 0, 255)
    return sharpened.astype(np.uint8)


def sobel_magnitude(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        image = to_grayscale(image)

    # kernel for horizontal edges
    gx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float)

    # kernel or vertical edges
    gy = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=float)

    # convolve both kernels
    grad_x = convolve2d(image, gx)
    grad_y = convolve2d(image, gy)

    # Compute magnitude of both gradients using distance formula
    magnitude = np.sqrt(grad_x**2 + grad_y**2)

    # interpolate into [0, 255] interval
    magnitude = (magnitude / magnitude.max()) * 255
    return magnitude.astype(np.uint8)
