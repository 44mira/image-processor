import numpy as np


def get_histogram(channel: np.ndarray):
    """
    Get a histogram from a single channel matrix.

    Args:
        channel: 2-d array of values for the histogram

    Returns:
        (counts, bin_edges) tuple from np.histogram

    Raises:
        ValueError: if shape is invalid (not 2d)
    """

    if channel.ndim != 2:
        raise ValueError("Input must be a 2d array.")

    return np.histogram(channel, bins=256, range=(0, 255))
