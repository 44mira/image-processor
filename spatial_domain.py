import numpy as np

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
