"""
Pytest tests for PCX header extraction module
"""

import os
import struct

import pytest

from pcx_header import (
    InvalidPCXError,
    PCXError,
    PCXHeader,
    read_256_color_palette,
)


def create_test_pcx_header(
    manufacturer=0x0A,
    version=5,
    encoding=1,
    bits_per_pixel=8,
    xmin=0,
    ymin=0,
    xmax=639,
    ymax=479,
    hdpi=300,
    vdpi=300,
    num_planes=1,
    bytes_per_line=640,
    palette_type=1,
):
    """Helper function to create a valid PCX header for testing"""

    # Create EGA palette (48 bytes of zeros for simplicity)
    colormap = b"\x00" * 48

    # Create reserved sections
    reserved = 0
    hscreen_size = 0
    vscreen_size = 0
    filler = b"\x00" * 54

    # Pack the header
    # Format: <BBBBHHHHHH48sBBHHHH54s (128 bytes total)
    header = struct.pack(
        "<BBBBHHHHHH48sBBHHHH54s",
        manufacturer,  # 0: Byte
        version,  # 1: Byte
        encoding,  # 2: Byte
        bits_per_pixel,  # 3: Byte
        xmin,  # 4: Short
        ymin,  # 5: Short
        xmax,  # 6: Short
        ymax,  # 7: Short
        hdpi,  # 8: Short
        vdpi,  # 9: Short
        colormap,  # 10: 48 bytes
        reserved,  # 11: Byte
        num_planes,  # 12: Byte
        bytes_per_line,  # 13: Short
        palette_type,  # 14: Short
        hscreen_size,  # 15: Short
        vscreen_size,  # 16: Short
        filler,  # 17: 54 bytes
    )

    return header


class TestPCXHeaderParsing:
    """Test PCX header parsing functionality"""

    @pytest.mark.parametrize(
        "version,bits_per_pixel,num_planes,width,height,expected_mode",
        [
            (5, 8, 1, 640, 480, "8-bit (256 colors)"),
            (5, 8, 3, 800, 600, "24-bit True Color (RGB)"),
            (2, 4, 1, 320, 200, "4-bit (16 colors)"),
            (0, 1, 1, 640, 480, "1-bit Monochrome"),
            (2, 2, 1, 320, 200, "2-bit (4 colors)"),
        ],
    )
    def test_valid_headers(
        self,
        tmp_path,
        version,
        bits_per_pixel,
        num_planes,
        width,
        height,
        expected_mode,
    ):
        """Test parsing various valid PCX headers"""
        pcx_file = (
            tmp_path / f"test_{version}_{bits_per_pixel}_{num_planes}.pcx"
        )
        header_data = create_test_pcx_header(
            version=version,
            bits_per_pixel=bits_per_pixel,
            num_planes=num_planes,
            xmax=width - 1,
            ymax=height - 1,
            bytes_per_line=((width * bits_per_pixel + 7) // 8 + 1)
            & ~1,  # Ensure even
        )
        pcx_file.write_bytes(header_data)

        header = PCXHeader.parse_pcx_header(str(pcx_file))

        assert header.manufacturer == 0x0A
        assert header.version == version
        assert header.encoding == 1
        assert header.bits_per_pixel == bits_per_pixel
        assert header.num_planes == num_planes
        assert header.width == width
        assert header.height == height
        assert header.color_mode == expected_mode

    @pytest.mark.parametrize(
        "manufacturer,expected_error",
        [
            (0x00, "Invalid manufacturer byte"),
            (0xFF, "Invalid manufacturer byte"),
            (0x0B, "Invalid manufacturer byte"),
        ],
    )
    def test_invalid_manufacturer(self, tmp_path, manufacturer, expected_error):
        """Test that invalid manufacturer bytes raise errors"""
        pcx_file = tmp_path / f"bad_manufacturer_{manufacturer:02X}.pcx"
        header_data = create_test_pcx_header(manufacturer=manufacturer)
        pcx_file.write_bytes(header_data)

        with pytest.raises(InvalidPCXError, match=expected_error):
            PCXHeader.parse_pcx_header(str(pcx_file))

    @pytest.mark.parametrize(
        "encoding,expected_error",
        [
            (2, "Unsupported encoding"),
            (255, "Unsupported encoding"),
        ],
    )
    def test_invalid_encoding(self, tmp_path, encoding, expected_error):
        """Test that unsupported encodings raise errors"""
        pcx_file = tmp_path / f"bad_encoding_{encoding}.pcx"
        header_data = create_test_pcx_header(encoding=encoding)
        pcx_file.write_bytes(header_data)

        with pytest.raises(InvalidPCXError, match=expected_error):
            PCXHeader.parse_pcx_header(str(pcx_file))

    def test_valid_uncompressed_encoding(self, tmp_path):
        """Test that encoding 0 (uncompressed) is valid"""
        pcx_file = tmp_path / "uncompressed.pcx"
        header_data = create_test_pcx_header(encoding=0)
        pcx_file.write_bytes(header_data)

        header = PCXHeader.parse_pcx_header(str(pcx_file))
        assert header.encoding == 0

    @pytest.mark.parametrize(
        "xmin,xmax,ymin,ymax,expected_error",
        [
            (100, 50, 0, 100, "Invalid X dimensions"),
            (0, 100, 200, 100, "Invalid Y dimensions"),
            (500, 100, 500, 100, "Invalid X dimensions"),  # Both invalid
        ],
    )
    def test_invalid_dimensions(
        self, tmp_path, xmin, xmax, ymin, ymax, expected_error
    ):
        """Test that invalid dimensions raise errors"""
        pcx_file = tmp_path / f"bad_dims_{xmin}_{xmax}_{ymin}_{ymax}.pcx"
        header_data = create_test_pcx_header(
            xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax
        )
        pcx_file.write_bytes(header_data)

        with pytest.raises(InvalidPCXError, match=expected_error):
            PCXHeader.parse_pcx_header(str(pcx_file))

    @pytest.mark.parametrize(
        "bytes_per_line",
        [
            639,  # Odd
            101,  # Odd
            1,  # Odd
        ],
    )
    def test_odd_bytes_per_line(self, tmp_path, bytes_per_line):
        """Test that odd bytes_per_line raises error"""
        pcx_file = tmp_path / f"odd_bytes_{bytes_per_line}.pcx"
        header_data = create_test_pcx_header(bytes_per_line=bytes_per_line)
        pcx_file.write_bytes(header_data)

        with pytest.raises(
            InvalidPCXError, match="Bytes per line must be even"
        ):
            PCXHeader.parse_pcx_header(str(pcx_file))

    @pytest.mark.parametrize(
        "file_size",
        [
            0,
            50,
            100,
            127,
        ],
    )
    def test_file_too_small(self, tmp_path, file_size):
        """Test that files smaller than 128 bytes raise error"""
        pcx_file = tmp_path / f"too_small_{file_size}.pcx"
        pcx_file.write_bytes(b"\x00" * file_size)

        with pytest.raises(InvalidPCXError, match="File too small"):
            PCXHeader.parse_pcx_header(str(pcx_file))

    def test_nonexistent_file(self):
        """Test that nonexistent files raise appropriate error"""
        with pytest.raises(PCXError, match="Failed to read file"):
            PCXHeader.parse_pcx_header("/nonexistent/path/to/file.pcx")


class TestPCXHeaderObject:
    """Test PCXHeader object methods"""

    @pytest.mark.parametrize(
        "version,expected_string",
        [
            (0, "v2.5 PC Paintbrush"),
            (2, "v2.8 with palette"),
            (3, "v2.8 without palette"),
            (4, "PC Paintbrush for Windows"),
            (5, "v3.0+ (includes 24-bit support)"),
            (99, "Unknown (version 99)"),
        ],
    )
    def test_version_string(self, version, expected_string):
        """Test version string formatting"""
        header = PCXHeader(
            manufacturer=0x0A,
            version=version,
            encoding=1,
            bits_per_pixel=8,
            xmin=0,
            ymin=0,
            xmax=99,
            ymax=99,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=100,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        assert header.get_version_string() == expected_string

    @pytest.mark.parametrize(
        "palette_type,expected_string",
        [
            (1, "Color/B&W"),
            (2, "Grayscale"),
            (99, "Unknown (99)"),
        ],
    )
    def test_palette_type_string(self, palette_type, expected_string):
        """Test palette type string formatting"""
        header = PCXHeader(
            manufacturer=0x0A,
            version=5,
            encoding=1,
            bits_per_pixel=8,
            xmin=0,
            ymin=0,
            xmax=99,
            ymax=99,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=100,
            palette_type=palette_type,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        assert header.get_palette_type_string() == expected_string

    @pytest.mark.parametrize(
        "bits_per_pixel,num_planes,expected_mode",
        [
            (1, 1, "1-bit Monochrome"),
            (2, 1, "2-bit (4 colors)"),
            (4, 1, "4-bit (16 colors)"),
            (8, 1, "8-bit (256 colors)"),
            (8, 3, "24-bit True Color (RGB)"),
            (1, 2, "2-bit (4 colors)"),
            (1, 4, "4-bit (16 colors)"),
            (16, 1, "Unknown (16-bit)"),
        ],
    )
    def test_color_mode_determination(
        self, bits_per_pixel, num_planes, expected_mode
    ):
        """Test color mode string generation"""
        header = PCXHeader(
            manufacturer=0x0A,
            version=5,
            encoding=1,
            bits_per_pixel=bits_per_pixel,
            xmin=0,
            ymin=0,
            xmax=99,
            ymax=99,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=num_planes,
            bytes_per_line=100,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        assert header.color_mode == expected_mode

    def test_colormap_extraction(self):
        """Test EGA palette RGB extraction"""
        # Create a simple palette with known values
        palette_data = b""
        for i in range(16):
            r = i * 16
            g = i * 8
            b = i * 4
            palette_data += bytes([r, g, b])

        header = PCXHeader(
            manufacturer=0x0A,
            version=2,
            encoding=1,
            bits_per_pixel=4,
            xmin=0,
            ymin=0,
            xmax=99,
            ymax=99,
            hdpi=300,
            vdpi=300,
            colormap=palette_data,
            reserved=0,
            num_planes=1,
            bytes_per_line=100,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        palette = header.get_colormap_rgb()

        assert len(palette) == 16
        assert palette[0] == (0, 0, 0)
        assert palette[1] == (16, 8, 4)
        assert palette[15] == (240, 120, 60)

    @pytest.mark.parametrize(
        "xmin,ymin,xmax,ymax,expected_width,expected_height",
        [
            (0, 0, 99, 99, 100, 100),
            (10, 20, 109, 119, 100, 100),
            (0, 0, 639, 479, 640, 480),
            (5, 5, 324, 204, 320, 200),
        ],
    )
    def test_computed_dimensions(
        self, xmin, ymin, xmax, ymax, expected_width, expected_height
    ):
        """Test that width and height are computed correctly"""
        header = PCXHeader(
            manufacturer=0x0A,
            version=5,
            encoding=1,
            bits_per_pixel=8,
            xmin=xmin,
            ymin=ymin,
            xmax=xmax,
            ymax=ymax,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=expected_width,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        assert header.width == expected_width
        assert header.height == expected_height

    def test_validation_passes(self):
        """Test that valid header passes validation"""
        header = PCXHeader(
            manufacturer=0x0A,
            version=5,
            encoding=1,
            bits_per_pixel=8,
            xmin=0,
            ymin=0,
            xmax=99,
            ymax=99,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=100,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        is_valid, errors = header.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validation_fails_multiple_errors(self):
        """Test that invalid header fails validation with multiple errors"""
        header = PCXHeader(
            manufacturer=0xFF,  # Invalid
            version=5,
            encoding=2,  # Invalid encoding
            bits_per_pixel=8,
            xmin=100,
            ymin=0,
            xmax=50,
            ymax=99,  # Invalid dimensions
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=101,  # Odd number - invalid
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        is_valid, errors = header.validate()
        assert is_valid is False
        assert len(errors) > 0
        assert any("manufacturer" in e for e in errors)
        assert any("encoding" in e for e in errors)
        assert any("dimensions" in e for e in errors)
        assert any("even" in e for e in errors)


class TestRealPCXFiles:
    """Test parsing of actual PCX files"""

    @pytest.mark.parametrize(
        "file_name,expected_width,expected_height,expected_version,\
            expected_encoding,expected_color_mode",
        [
            ("Boat.pcx", 256, 256, 5, 1, "8-bit (256 colors)"),
            ("Lena_256.pcx", 256, 256, 5, 1, "8-bit (256 colors)"),
        ],
    )
    def test_real_pcx_files(
        self,
        file_name,
        expected_width,
        expected_height,
        expected_version,
        expected_encoding,
        expected_color_mode,
    ):
        """Test parsing real PCX files from test files directory"""
        file_path = os.path.join("test files", "pcx", file_name)

        # Skip if file doesn't exist
        if not os.path.exists(file_path):
            pytest.skip(f"PCX file not found: {file_path}")

        header = PCXHeader.parse_pcx_header(file_path)

        # Verify basic properties
        assert header.manufacturer == 0x0A
        assert header.version == expected_version
        assert header.encoding == expected_encoding
        assert header.width == expected_width
        assert header.height == expected_height
        assert header.color_mode == expected_color_mode

        # Verify validation passes
        is_valid, errors = header.validate()
        assert is_valid is True
        assert len(errors) == 0


class Test256ColorPalette:
    """Test 256-color palette extraction"""

    def test_read_256_color_palette_real_files(self):
        """Test reading 256-color palette from real PCX files"""
        # Only Lena_256.pcx has a 256-color palette
        # Boat.pcx is 8-bit but uses the 16-color EGA palette from header
        file_path = os.path.join("test files", "pcx", "Lena_256.pcx")

        # Skip if file doesn't exist
        if not os.path.exists(file_path):
            pytest.skip(f"PCX file not found: {file_path}")

        palette = read_256_color_palette(file_path)

        # Verify palette has 768 values (256 colors * 3 components)
        assert len(palette) == 768

        # Verify all values are in valid range
        assert all(0 <= val <= 255 for val in palette)

        # Verify palette has varied colors (not all zeros)
        assert len(set(palette)) > 1

    def test_read_palette_with_valid_marker(self, tmp_path):
        """Test reading palette from file with valid marker"""
        pcx_file = tmp_path / "test_palette.pcx"

        # Create minimal PCX file with palette
        header_data = create_test_pcx_header()

        # Create some dummy image data
        image_data = b"\x00" * 100

        # Create palette with marker - RGB triplets
        palette_marker = b"\x0c"
        # Create palette: [R0, G0, B0, R1, G1, B1, ..., R255, G255, B255]
        palette_data = bytearray()
        for i in range(256):
            palette_data.extend([i, i, i])  # Gray scale

        pcx_file.write_bytes(
            header_data + image_data + palette_marker + bytes(palette_data)
        )

        palette = read_256_color_palette(str(pcx_file))

        assert len(palette) == 768
        # First color should be (0, 0, 0)
        assert palette[0:3] == [0, 0, 0]
        # Color at index 100 should be (100, 100, 100)
        assert palette[300:303] == [100, 100, 100]

    def test_read_palette_missing_marker(self, tmp_path):
        """Test error when palette marker is missing"""
        pcx_file = tmp_path / "no_marker.pcx"

        header_data = create_test_pcx_header()
        image_data = b"\x00" * 100

        # Wrong marker (not 0x0C)
        palette_marker = b"\xff"
        palette_data = b"\x00" * 768

        pcx_file.write_bytes(
            header_data + image_data + palette_marker + palette_data
        )

        with pytest.raises(
            InvalidPCXError, match="Missing or invalid 256-color palette marker"
        ):
            read_256_color_palette(str(pcx_file))

    def test_read_palette_file_too_small(self, tmp_path):
        """Test error when file is too small to contain palette"""
        pcx_file = tmp_path / "too_small.pcx"

        # File smaller than minimum size (128 header + 769 palette)
        pcx_file.write_bytes(b"\x00" * 500)

        with pytest.raises(
            InvalidPCXError, match="File too small for 256-color palette"
        ):
            read_256_color_palette(str(pcx_file))

    def test_read_palette_nonexistent_file(self):
        """Test error when file doesn't exist"""
        with pytest.raises(PCXError, match="Failed to read palette from file"):
            read_256_color_palette("/nonexistent/path/to/file.pcx")
