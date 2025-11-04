"""
PCX Utilities for PyQt6 GUI

This module provides functions to convert PCX files to QImage objects
and create palette visualizations.
"""

from PyQt6.QtGui import QColor, QImage

from pcx_header import InvalidPCXError, PCXHeader, read_256_color_palette
from pcx_rle import read_and_decompress_pcx_data


def pcx_to_qimage(file_path: str, header: PCXHeader) -> QImage:
    """
    Convert PCX pixel data to QImage.

    Args:
        file_path: Path to the PCX file
        header: Parsed PCX header

    Returns:
        QImage object

    Raises:
        ValueError: If color mode is not supported
    """
    # Decompress pixel data
    pixel_data = read_and_decompress_pcx_data(file_path, header)

    # Handle 8-bit indexed color
    if header.bits_per_pixel == 8 and header.num_planes == 1:
        return _create_8bit_qimage(file_path, pixel_data, header)
    else:
        raise ValueError(
            f"Unsupported PCX format: {header.color_mode}. "
            f"Currently only 8-bit indexed color is supported."
        )


def _create_8bit_qimage(
    file_path: str, pixel_data: bytes, header: PCXHeader
) -> QImage:
    """
    Create QImage from 8-bit indexed PCX data.

    Handles both:
    - 256-color palette (VGA palette at end of file)
    - Grayscale (no palette, direct gray values)

    Args:
        file_path: Path to PCX file
        pixel_data: Decompressed pixel data
        header: PCX header

    Returns:
        QImage with Format_Indexed8
    """
    # Create QImage
    image = QImage(header.width, header.height, QImage.Format.Format_Indexed8)

    # Try to read 256-color palette
    try:
        palette_data = read_256_color_palette(file_path)
        # Convert to QColor RGB values
        color_table = []
        for i in range(256):
            r = palette_data[i * 3]
            g = palette_data[i * 3 + 1]
            b = palette_data[i * 3 + 2]
            color_table.append(QColor(r, g, b).rgb())
        image.setColorTable(color_table)
    except InvalidPCXError:
        # No 256-color palette found - assume grayscale
        color_table = [QColor(i, i, i).rgb() for i in range(256)]
        image.setColorTable(color_table)

    # Fill pixel data scanline by scanline
    for y in range(header.height):
        line_offset = y * header.bytes_per_line
        line_data = pixel_data[line_offset : line_offset + header.width]

        for x in range(header.width):
            image.setPixel(x, y, line_data[x])

    return image


def create_palette_image(file_path: str, header: PCXHeader) -> QImage:
    """
    Create a visual representation of the color palette.

    Creates a 256x16 pixel image showing all colors in the palette.

    Args:
        file_path: Path to PCX file
        header: PCX header

    Returns:
        QImage showing palette colors, or None if no palette
    """
    # Try to read 256-color palette
    try:
        palette_data = read_256_color_palette(file_path)
    except InvalidPCXError:
        # No palette - create grayscale palette
        palette_data = []
        for i in range(256):
            palette_data.extend([i, i, i])

    # Create palette visualization: 16 rows x 16 columns
    # Each color is a 16x16 square
    square_size = 16
    width = 16 * square_size  # 256 pixels
    height = 16 * square_size  # 256 pixels

    palette_image = QImage(width, height, QImage.Format.Format_RGB888)

    for color_idx in range(256):
        r = palette_data[color_idx * 3]
        g = palette_data[color_idx * 3 + 1]
        b = palette_data[color_idx * 3 + 2]

        # Calculate position in 16x16 grid
        row = color_idx // 16
        col = color_idx % 16

        # Fill the square
        for dy in range(square_size):
            for dx in range(square_size):
                x = col * square_size + dx
                y = row * square_size + dy
                palette_image.setPixel(x, y, QColor(r, g, b).rgb())

    return palette_image
