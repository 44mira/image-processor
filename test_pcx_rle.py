"""
Pytest tests for PCX RLE decompression module
"""

import pytest

from pcx_header import InvalidPCXError, PCXHeader
from pcx_rle import decompress_pcx_rle, read_and_decompress_pcx_data


class TestRLEDecompression:
    """Test PCX RLE decompression functionality"""

    def test_literal_bytes(self):
        """Test decompression of literal (non-encoded) bytes"""
        # Bytes with top 2 bits not set (0x00-0x3F and 0x80-0xBF are literals)
        compressed = bytes([0x01, 0x02, 0x03, 0x3F, 0x80, 0xBF])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=6, num_planes=1, height=1
        )

        assert result == compressed

    def test_rle_encoded_bytes(self):
        """Test decompression of RLE-encoded bytes"""
        # 0xC5 = 11000101 = run of 5, value 0xFF
        compressed = bytes([0xC5, 0xFF])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=5, num_planes=1, height=1
        )

        assert result == bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF])

    def test_mixed_literal_and_rle(self):
        """Test decompression with mix of literal and RLE bytes"""
        # 0x01 (literal), 0xC3 (run of 3), 0xAA (value), 0x05 (literal)
        compressed = bytes([0x01, 0xC3, 0xAA, 0x05])
        expected = bytes([0x01, 0xAA, 0xAA, 0xAA, 0x05])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=5, num_planes=1, height=1
        )

        assert result == expected

    def test_maximum_run_length(self):
        """Test maximum RLE run length of 63"""
        # 0xFF = 11111111 = run of 63, value 0x00
        compressed = bytes([0xFF, 0x00])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=63, num_planes=1, height=1
        )

        assert result == bytes([0x00] * 63)
        assert len(result) == 63

    def test_minimum_run_length(self):
        """Test minimum RLE run length of 1"""
        # 0xC1 = 11000001 = run of 1, value 0xAB
        compressed = bytes([0xC1, 0xAB])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=1, num_planes=1, height=1
        )

        assert result == bytes([0xAB])

    def test_multiple_scanlines(self):
        """Test decompression across multiple scanlines"""
        # 2 lines, 3 bytes each = 6 total bytes
        # Line 1: 0xC3 0xFF (3 bytes of 0xFF)
        # Line 2: 0x01 0x02 0x03 (3 literal bytes)
        compressed = bytes([0xC3, 0xFF, 0x01, 0x02, 0x03])
        expected = bytes([0xFF, 0xFF, 0xFF, 0x01, 0x02, 0x03])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=3, num_planes=1, height=2
        )

        assert result == expected

    def test_multiple_planes(self):
        """Test decompression with multiple color planes"""
        # 3 planes, 2 bytes per line, 1 line = 6 total bytes
        compressed = bytes([0xC6, 0xAA])  # Run of 6 0xAA

        result = decompress_pcx_rle(
            compressed, bytes_per_line=2, num_planes=3, height=1
        )

        assert result == bytes([0xAA] * 6)

    def test_incomplete_rle_data_missing_value(self):
        """Test error when RLE count byte is present
        but value byte is missing"""
        # 0xC5 indicates run of 5, but no value byte follows
        compressed = bytes([0xC5])

        with pytest.raises(InvalidPCXError, match="missing value byte"):
            decompress_pcx_rle(
                compressed, bytes_per_line=5, num_planes=1, height=1
            )

    def test_incomplete_rle_data_insufficient_bytes(self):
        """Test error when decompressed data is shorter than expected"""
        # Only produces 3 bytes, but expecting 5
        compressed = bytes([0xC3, 0xFF])

        with pytest.raises(InvalidPCXError, match="Incomplete RLE data"):
            decompress_pcx_rle(
                compressed, bytes_per_line=5, num_planes=1, height=1
            )

    def test_excess_data_is_trimmed(self):
        """Test that excess decompressed data is trimmed"""
        # Produces 5 bytes, but only need 3
        compressed = bytes([0xC5, 0xAA])

        result = decompress_pcx_rle(
            compressed, bytes_per_line=3, num_planes=1, height=1
        )

        assert len(result) == 3
        assert result == bytes([0xAA, 0xAA, 0xAA])

    def test_empty_compressed_data(self):
        """Test handling of empty compressed data"""
        compressed = bytes([])

        with pytest.raises(InvalidPCXError, match="Incomplete RLE data"):
            decompress_pcx_rle(
                compressed, bytes_per_line=1, num_planes=1, height=1
            )

    @pytest.mark.parametrize(
        "byte_value",
        [
            0xC0,  # 11000000 - run of 0 (edge case)
            0xC1,  # 11000001 - run of 1
            0xFE,  # 11111110 - run of 62
            0xFF,  # 11111111 - run of 63
        ],
    )
    def test_rle_marker_boundary_cases(self, byte_value):
        """Test RLE markers at boundary values"""
        run_count = byte_value & 0x3F
        if run_count == 0:
            # Run of 0 should not produce any output
            compressed = bytes([byte_value, 0xAA])
            result = decompress_pcx_rle(
                compressed, bytes_per_line=0, num_planes=1, height=1
            )
            assert len(result) == 0
        else:
            compressed = bytes([byte_value, 0xAA])
            result = decompress_pcx_rle(
                compressed, bytes_per_line=run_count, num_planes=1, height=1
            )
            assert len(result) == run_count
            assert all(b == 0xAA for b in result)


class TestReadAndDecompressPCXData:
    """Test the integrated file reading and decompression function"""

    def test_rle_encoded_file(self, tmp_path):
        """Test reading and decompressing an RLE-encoded PCX file"""
        pcx_file = tmp_path / "test_rle.pcx"

        # Create a simple header (128 bytes)
        header_bytes = b"\x0a" + b"\x00" * 127

        # Create RLE-encoded image data: 0xC5 0xFF = 5 bytes of 0xFF
        image_data = bytes([0xC5, 0xFF])

        pcx_file.write_bytes(header_bytes + image_data)

        # Create a mock header object
        header = PCXHeader(
            manufacturer=0x0A,
            version=5,
            encoding=1,  # RLE
            bits_per_pixel=8,
            xmin=0,
            ymin=0,
            xmax=4,
            ymax=0,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=5,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        result = read_and_decompress_pcx_data(str(pcx_file), header)

        assert result == bytes([0xFF] * 5)

    def test_uncompressed_file(self, tmp_path):
        """Test reading an uncompressed PCX file"""
        pcx_file = tmp_path / "test_uncompressed.pcx"

        # Create a simple header (128 bytes)
        header_bytes = b"\x0a" + b"\x00" * 127

        # Create uncompressed image data
        image_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05])

        pcx_file.write_bytes(header_bytes + image_data)

        # Create a mock header object with encoding=0
        header = PCXHeader(
            manufacturer=0x0A,
            version=5,
            encoding=0,  # Uncompressed
            bits_per_pixel=8,
            xmin=0,
            ymin=0,
            xmax=4,
            ymax=0,
            hdpi=300,
            vdpi=300,
            colormap=b"\x00" * 48,
            reserved=0,
            num_planes=1,
            bytes_per_line=5,
            palette_type=1,
            hscreen_size=0,
            vscreen_size=0,
            filler=b"\x00" * 54,
        )

        result = read_and_decompress_pcx_data(str(pcx_file), header)

        # Should return raw data unchanged
        assert result == image_data


class TestRealPCXFiles:
    """Test RLE decompression with actual PCX files"""

    @pytest.mark.parametrize(
        "file_name,expected_width,expected_height",
        [
            ("Boat.pcx", 256, 256),
            ("Lena_256.pcx", 256, 256),
        ],
    )
    def test_real_pcx_decompression(
        self, file_name, expected_width, expected_height
    ):
        """Test decompressing real PCX files from test files directory"""
        import os

        file_path = os.path.join("test files", "pcx", file_name)

        # Skip if file doesn't exist
        if not os.path.exists(file_path):
            pytest.skip(f"PCX file not found: {file_path}")

        real_header = PCXHeader.parse_pcx_header(file_path)

        # Decompress the file
        decompressed = read_and_decompress_pcx_data(file_path, real_header)

        # Verify decompressed data size matches expected
        expected_size = (
            real_header.bytes_per_line
            * real_header.num_planes
            * real_header.height
        )
        assert len(decompressed) == expected_size

        # Verify decompressed data is not empty and contains varied values
        assert (
            len(set(decompressed)) > 1
        )  # Should have more than 1 unique value
