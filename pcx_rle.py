"""
PCX RLE Decompression Module

This module handles Run-Length Encoding (RLE) decompression for PCX image data.
PCX files use a simple RLE scheme where the top 2 bits indicate a run-length count.

Reference: ZSoft PCX File Format Technical Reference Manual
"""

from pcx_header import InvalidPCXError, PCXHeader


def decompress_pcx_rle(
    compressed_data: bytes, bytes_per_line: int, num_planes: int, height: int
) -> bytes:
    """
    Decompress PCX RLE-encoded image data

    PCX RLE encoding rules:
    - If the top 2 bits are set (0xC0), the lower 6 bits represent the run count (1-63)
      and the next byte is the value to repeat
    - Otherwise, the byte is a literal value (run count of 1)

    Args:
        compressed_data: The compressed image data (after 128-byte header)
        bytes_per_line: Bytes per scanline per plane from header
        num_planes: Number of color planes from header
        height: Image height in pixels

    Returns:
        Decompressed image data

    Raises:
        InvalidPCXError: If RLE data is corrupted or incomplete
    """
    decompressed = bytearray()
    total_bytes_needed = bytes_per_line * num_planes * height
    i = 0

    try:
        while len(decompressed) < total_bytes_needed and i < len(compressed_data):
            byte = compressed_data[i]
            i += 1

            # Check if top 2 bits are set (0xC0 = 11000000)
            if (byte & 0xC0) == 0xC0:
                # This is a run-length count
                run_count = byte & 0x3F  # Lower 6 bits (mask with 00111111)

                if i >= len(compressed_data):
                    raise InvalidPCXError(
                        "Unexpected end of RLE data (missing value byte)"
                    )

                value = compressed_data[i]
                i += 1

                # Repeat the value run_count times
                decompressed.extend([value] * run_count)
            else:
                # Literal value (not encoded)
                decompressed.append(byte)

        if len(decompressed) < total_bytes_needed:
            raise InvalidPCXError(
                f"Incomplete RLE data: got {len(decompressed)} bytes, expected {total_bytes_needed}"
            )

        # Return exactly the amount needed (trim any excess)
        return bytes(decompressed[:total_bytes_needed])

    except IndexError:
        raise InvalidPCXError("RLE data corrupted: unexpected end of data")


def read_and_decompress_pcx_data(file_path: str, header: PCXHeader) -> bytes:
    """
    Read PCX file and decompress image data if RLE encoded

    Args:
        file_path: Path to the PCX file
        header: PCXHeader object with parsed header information

    Returns:
        Decompressed image data (or raw data if not RLE encoded)

    Raises:
        InvalidPCXError: If file cannot be read or RLE decompression fails
    """
    try:
        with open(file_path, "rb") as f:
            # Skip the 128-byte header
            f.seek(128)

            # Read the rest of the file (image data)
            image_data = f.read()

            # Check encoding type
            if header.encoding == 1:
                # RLE encoded - decompress
                return decompress_pcx_rle(
                    image_data, header.bytes_per_line, header.num_planes, header.height
                )
            else:
                # Not RLE encoded - return as is
                return image_data

    except IOError as e:
        raise InvalidPCXError(f"Failed to read PCX image data: {e}")
