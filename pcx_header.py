"""
PCX Header Extraction Module

This module handles parsing and validation of PCX file headers.
PCX header is always 128 bytes at the start of the file.

Reference: ZSoft PCX File Format Technical Reference Manual
"""

import struct
from dataclasses import dataclass
from typing import Self


class PCXError(Exception):
    """Base exception for PCX-related errors"""

    pass


class InvalidPCXError(PCXError):
    """Raised when PCX file is invalid or corrupted"""

    pass


@dataclass
class PCXHeader:
    """
    PCX file header structure (128 bytes total)

    All multi-byte integers are stored in little-endian format.

    Should be constructed using `PCXHeader.parse_pcx_header(file_name)`.
    """

    # Raw header fields
    manufacturer: int  # Offset 0: Should be 0x0A
    version: int  # Offset 1: 0,2,3,4,5
    encoding: int  # Offset 2: 1 = RLE
    bits_per_pixel: int  # Offset 3: 1,2,4,8
    xmin: int  # Offset 4-5: Image bounds
    ymin: int  # Offset 6-7
    xmax: int  # Offset 8-9
    ymax: int  # Offset 10-11
    hdpi: int  # Offset 12-13: Horizontal DPI
    vdpi: int  # Offset 14-15: Vertical DPI
    colormap: bytes  # Offset 16-63: 16-color palette (48 bytes)
    reserved: int  # Offset 64: Reserved (should be 0)
    num_planes: int  # Offset 65: Number of color planes
    bytes_per_line: int  # Offset 66-67: Bytes per scanline per plane (even)
    palette_type: int  # Offset 68-69: 1=color/BW, 2=grayscale
    hscreen_size: int  # Offset 70-71: Horizontal screen size
    vscreen_size: int  # Offset 72-73: Vertical screen size
    filler: bytes  # Offset 74-127: Reserved (54 bytes)

    # Computed properties
    width: int = 0
    height: int = 0
    color_mode: str = ""

    def __post_init__(self):
        """Calculate derived properties after initialization"""
        self.width = self.xmax - self.xmin + 1
        self.height = self.ymax - self.ymin + 1
        self.color_mode = self._determine_color_mode()

    def _determine_color_mode(self) -> str:
        """
        Determine the color mode based on bits per pixel and number of planes
        """
        total_bits = self.bits_per_pixel * self.num_planes

        if total_bits == 1:
            return "1-bit Monochrome"
        elif total_bits == 2:
            return "2-bit (4 colors)"
        elif total_bits == 4:
            return "4-bit (16 colors)"
        elif total_bits == 8:
            return "8-bit (256 colors)"
        elif total_bits == 24:
            return "24-bit True Color (RGB)"
        else:
            return f"Unknown ({total_bits}-bit)"

    def get_version_string(self) -> str:
        """Get human-readable version string"""
        version_map = {
            0: "v2.5 PC Paintbrush",
            2: "v2.8 with palette",
            3: "v2.8 without palette",
            4: "PC Paintbrush for Windows",
            5: "v3.0+ (includes 24-bit support)",
        }
        return version_map.get(
            self.version,
            f"Unknown (version {self.version})",
        )

    def get_palette_type_string(self) -> str:
        """Get human-readable palette type"""
        if self.palette_type == 1:
            return "Color/B&W"
        elif self.palette_type == 2:
            return "Grayscale"
        else:
            return f"Unknown ({self.palette_type})"

    def get_colormap_rgb(self) -> list[tuple[int, int, int]]:
        """
        Extract the 16-color EGA palette as list of RGB tuples

        Returns:
            List of 16 (R, G, B) tuples
        """
        palette = []
        for i in range(16):
            offset = i * 3
            r = self.colormap[offset]
            g = self.colormap[offset + 1]
            b = self.colormap[offset + 2]
            palette.append((r, g, b))
        return palette

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the PCX header

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check manufacturer byte
        if self.manufacturer != 0x0A:
            errors.append(
                f"Invalid manufacturer byte: 0x{self.manufacturer:02X} "
                "(expected 0x0A)"
            )

        # Check encoding
        if self.encoding not in [0, 1]:
            errors.append(
                f"Unsupported encoding: {self.encoding} "
                "(only 0=uncompressed and 1=RLE are supported)"
            )

        # Check version
        if self.version not in [0, 2, 3, 4, 5]:
            errors.append(f"Unknown version: {self.version}")

        # Check bits per pixel
        if self.bits_per_pixel not in [1, 2, 4, 8]:
            errors.append(f"Invalid bits per pixel: {self.bits_per_pixel}")

        # Check image dimensions
        if self.xmax < self.xmin:
            errors.append(
                f"Invalid X dimensions: xmax ({self.xmax}) < xmin ({self.xmin})"
            )

        if self.ymax < self.ymin:
            errors.append(
                f"Invalid Y dimensions: ymax ({self.ymax}) < ymin ({self.ymin})"
            )

        if self.width <= 0 or self.height <= 0:
            errors.append(f"Invalid image size: {self.width}x{self.height}")

        # Check bytes per line
        if self.bytes_per_line % 2 != 0:
            errors.append(f"Bytes per line must be even: {self.bytes_per_line}")

        if self.bytes_per_line < ((self.width * self.bits_per_pixel + 7) // 8):
            errors.append(
                f"Bytes per line ({self.bytes_per_line}) too small for image "
                f"width ({self.width})"
            )

        # Check number of planes
        if self.num_planes not in [1, 3, 4]:
            errors.append(f"Unusual number of planes: {self.num_planes}")

        return (len(errors) == 0, errors)

    def __str__(self) -> str:
        """String representation of header information"""
        is_valid, errors = self.validate()

        encoding = f"Unknown ({self.encoding})"
        if self.encoding == 0:
            encoding = "Uncompressed"
        elif self.encoding == 1:
            encoding = "RLE"

        lines = [
            "PCX Header Information",
            "=" * 50,
            f"Version:          {self.get_version_string()}",
            f"Encoding:         {encoding}",
            f"Dimensions:       {self.width} x {self.height} pixels",
            f"Color Mode:       {self.color_mode}",
            f"Bits per Pixel:   {self.bits_per_pixel}",
            f"Number of Planes: {self.num_planes}",
            f"Bytes per Line:   {self.bytes_per_line}",
            f"Resolution:       {self.hdpi} x {self.vdpi} DPI",
            f"Palette Type:     {self.get_palette_type_string()}",
            f"Valid:            {'Yes' if is_valid else 'No'}",
        ]

        if not is_valid:
            lines.append("\nValidation Errors:")
            for error in errors:
                lines.append(f"  - {error}")

        return "\n".join(lines)

    @classmethod
    def parse_pcx_header(cls, file_path: str) -> Self:
        """
        Parse PCX header from a file, should be used as the main constructor.

        Args:
            file_path: Path to the PCX file

        Returns:
            PCXHeader object containing parsed header information

        Raises:
            InvalidPCXError: If file is not a valid PCX file
            PCXError: If file cannot be read
        """
        header_bytes = cls.read_pcx_header_raw(file_path)

        # Parse header using struct
        # Format string: little-endian
        # B = unsigned char (1 byte)
        # H = unsigned short (2 bytes, little-endian)
        # 48s = 48-byte string (EGA palette)
        # 54s = 54-byte string (reserved)

        try:
            fields = struct.unpack("<BBBBHHHHHH48sBBHHHH54s", header_bytes)

            # initialize parsed fields
            header = cls(*fields)

            # Validate the header
            is_valid, errors = header.validate()
            if not is_valid:
                error_msg = "Invalid PCX header:\n" + "\n".join(
                    f"  - {e}" for e in errors
                )
                raise InvalidPCXError(error_msg)

            return header

        except struct.error as e:
            raise InvalidPCXError(f"Failed to parse header structure: {e}")
        except IOError as e:
            raise PCXError(f"Failed to read file: {e}")

    @classmethod
    def read_pcx_header_raw(cls, file_path: str) -> bytes:
        """
        Read raw 128-byte header from PCX file

        Args:
            file_path: Path to the PCX file

        Returns:
            128 bytes of raw header data
        """
        with open(file_path, "rb") as f:
            header_bytes = f.read(128)
            cls._validate_header_length(header_bytes)

            return header_bytes

    @staticmethod
    def _validate_header_length(header_bytes):
        if len(header_bytes) < 128:
            raise InvalidPCXError(
                f"File too small: only {len(header_bytes)} bytes "
                "(need 128 for header)"
            )
