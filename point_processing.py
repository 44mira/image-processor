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

import cv2
import numpy as np


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


def to_negative(rgb_points: np.ndarray) -> np.ndarray:
    """Convert RGB point cloud to its negative."""
    if rgb_points.ndim not in (2, 3) or rgb_points.shape[-1] != 3:
        raise ValueError("Input must be an array with 3 channels (RGB).")

    negative = 255 - rgb_points
    return negative.astype(np.uint8)


def manual_threshold(intensities: np.ndarray, threshold: int) -> np.ndarray:
    """Convert intensities to black or white based on a manual threshold."""
    if not 0 <= threshold <= 255:
        raise ValueError("Threshold must be in range [0, 255].")

    return np.where(intensities >= threshold, 255, 0).astype(np.uint8)


def gamma_transform(
    image: np.ndarray, gamma: float, c: float = 1.0
) -> np.ndarray:
    """Apply Power-Law (Gamma) transformation to an RGB image."""
    if gamma <= 0:
        raise ValueError("Gamma must be greater than 0.")

    # Normalize to [0, 1]
    norm = image / 255.0

    # Apply power-law transformation per channel
    corrected = c * np.power(norm, gamma)

    # Rescale back to [0, 255]
    corrected = np.clip(corrected * 255.0, 0, 255).astype(np.uint8)

    return corrected


def histogram_equalization(image: np.ndarray) -> np.ndarray:
    """Perform histogram equalization on a grayscale image."""
    if len(image.shape) == 3:
        # Convert RGB to grayscale for histogram equalization
        image = np.dot(image[..., :3], [0.2989, 0.5870, 0.1140]).astype(
            np.uint8
        )

    # 1. Find range of intensity values
    min_intensity = np.min(image)
    max_intensity = np.max(image)
    intensity_range = max_intensity - min_intensity + 1

    # 2. Find frequency (histogram)
    hist, _bins = np.histogram(
        image.flatten(),
        bins=intensity_range,
        range=(min_intensity, max_intensity + 1),
    )

    # 3. Probability Density Function (PDF)
    pdf = hist / np.sum(hist)

    # 4. Cumulative Density Function (CDF)
    cdf = np.cumsum(pdf)

    # 5. Multiply by highest intensity value
    cdf_scaled = cdf * max_intensity

    # 6. Round off values
    cdf_rounded = np.round(cdf_scaled).astype(np.uint8)

    # Map old intensities to new equalized values
    equalized_image = cdf_rounded[image - min_intensity]

    return equalized_image


def histogram_equalization_rgb(image: np.ndarray) -> np.ndarray:
    """
    Perform histogram equalization on a color (RGB) image by
    converting it to HSV and equalizing only the Value (V) channel.
    """
    if image.ndim == 2:
        # Already grayscale
        return histogram_equalization(image)

    # Convert RGB → HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

    # Split into channels
    h, s, v = cv2.split(hsv)

    # Apply manual histogram equalization to the V channel
    v_eq = histogram_equalization(v)

    # Merge back the channels
    hsv_eq = cv2.merge([h, s, v_eq])

    # Convert back to RGB
    rgb_eq = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2RGB)

    return rgb_eq
