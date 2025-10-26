"""
Comprehensive tests for FileChunk value object.

Tests cover:
- Value object creation
- Immutability
- Validation rules
- Factory methods
- Size validation
- Data preview
"""

import pytest
from app.src.domain.upload.value_objects.file_chunk import FileChunk


class TestFileChunkCreation:
    """Test FileChunk creation and validation."""

    def test_create_chunk(self):
        """Test creating a valid chunk."""
        chunk = FileChunk(index=0, data=b"test data", size=9)

        assert chunk.index == 0
        assert chunk.data == b"test data"
        assert chunk.size == 9
        assert chunk.checksum == ""

    def test_create_chunk_with_checksum(self):
        """Test creating chunk with checksum."""
        chunk = FileChunk(index=0, data=b"test", size=4, checksum="abc123")

        assert chunk.checksum == "abc123"

    def test_create_factory_method(self):
        """Test factory method auto-calculates size."""
        chunk = FileChunk.create(index=5, data=b"hello world")

        assert chunk.index == 5
        assert chunk.data == b"hello world"
        assert chunk.size == 11

    def test_create_with_checksum(self):
        """Test factory method with checksum."""
        chunk = FileChunk.create(index=0, data=b"data", checksum="hash123")

        assert chunk.checksum == "hash123"


class TestFileChunkValidation:
    """Test FileChunk validation rules."""

    def test_negative_index_raises_error(self):
        """Test negative index raises ValueError."""
        with pytest.raises(ValueError, match="index cannot be negative"):
            FileChunk(index=-1, data=b"test", size=4)

    def test_negative_size_raises_error(self):
        """Test negative size raises ValueError."""
        with pytest.raises(ValueError, match="size cannot be negative"):
            FileChunk(index=0, data=b"test", size=-1)

    def test_size_mismatch_raises_error(self):
        """Test size mismatch with data length raises error."""
        with pytest.raises(ValueError, match="size does not match data length"):
            FileChunk(index=0, data=b"test", size=10)

    def test_empty_chunk_raises_error(self):
        """Test empty chunk raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FileChunk(index=0, data=b"", size=0)

    def test_zero_size_with_data_raises_error(self):
        """Test zero size with data raises error."""
        with pytest.raises(ValueError, match="size does not match data length"):
            FileChunk(index=0, data=b"x", size=0)


class TestFileChunkImmutability:
    """Test FileChunk immutability (frozen dataclass)."""

    def test_cannot_modify_index(self):
        """Test cannot modify index after creation."""
        chunk = FileChunk.create(index=0, data=b"test")

        with pytest.raises(AttributeError):
            chunk.index = 1

    def test_cannot_modify_data(self):
        """Test cannot modify data after creation."""
        chunk = FileChunk.create(index=0, data=b"test")

        with pytest.raises(AttributeError):
            chunk.data = b"new"

    def test_cannot_modify_size(self):
        """Test cannot modify size after creation."""
        chunk = FileChunk.create(index=0, data=b"test")

        with pytest.raises(AttributeError):
            chunk.size = 10

    def test_cannot_modify_checksum(self):
        """Test cannot modify checksum after creation."""
        chunk = FileChunk.create(index=0, data=b"test")

        with pytest.raises(AttributeError):
            chunk.checksum = "new"


class TestFileChunkSizeValidation:
    """Test chunk size validation."""

    def test_is_valid_size_true(self):
        """Test chunk within size limit is valid."""
        chunk = FileChunk.create(index=0, data=b"x" * 1000)
        max_size = 1024

        assert chunk.is_valid_size(max_size) is True

    def test_is_valid_size_exactly_max(self):
        """Test chunk exactly at max size is valid."""
        chunk = FileChunk.create(index=0, data=b"x" * 1024)
        max_size = 1024

        assert chunk.is_valid_size(max_size) is True

    def test_is_valid_size_exceeds_max(self):
        """Test chunk exceeding max size is invalid."""
        chunk = FileChunk.create(index=0, data=b"x" * 1025)
        max_size = 1024

        assert chunk.is_valid_size(max_size) is False

    def test_is_valid_size_very_small(self):
        """Test very small chunk is valid."""
        chunk = FileChunk.create(index=0, data=b"x")
        max_size = 1024

        assert chunk.is_valid_size(max_size) is True


class TestFileChunkDataPreview:
    """Test chunk data preview functionality."""

    def test_get_data_preview_default_length(self):
        """Test data preview with default length."""
        data = b"x" * 100
        chunk = FileChunk.create(index=0, data=data)

        preview = chunk.get_data_preview()

        assert len(preview) == 64  # 32 bytes * 2 (hex)
        assert isinstance(preview, str)

    def test_get_data_preview_custom_length(self):
        """Test data preview with custom length."""
        chunk = FileChunk.create(index=0, data=b"hello world")

        preview = chunk.get_data_preview(preview_length=5)

        assert preview == "68656c6c6f"  # "hello" in hex

    def test_get_data_preview_shorter_than_request(self):
        """Test preview when data shorter than requested."""
        chunk = FileChunk.create(index=0, data=b"hi")

        preview = chunk.get_data_preview(preview_length=10)

        assert preview == "6869"  # "hi" in hex

    def test_get_data_preview_empty_not_possible(self):
        """Test preview requires non-empty chunk."""
        # Empty chunks can't be created due to validation
        with pytest.raises(ValueError):
            FileChunk.create(index=0, data=b"")


class TestFileChunkStringRepresentation:
    """Test string representation."""

    def test_str_representation(self):
        """Test string representation of chunk."""
        chunk = FileChunk.create(index=5, data=b"x" * 1000)

        str_repr = str(chunk)

        assert "5" in str_repr
        assert "1000" in str_repr
        assert "Chunk" in str_repr


class TestFileChunkEquality:
    """Test chunk equality."""

    def test_equal_chunks(self):
        """Test equal chunks are equal."""
        chunk1 = FileChunk(index=0, data=b"test", size=4)
        chunk2 = FileChunk(index=0, data=b"test", size=4)

        assert chunk1 == chunk2

    def test_different_index_not_equal(self):
        """Test chunks with different index not equal."""
        chunk1 = FileChunk(index=0, data=b"test", size=4)
        chunk2 = FileChunk(index=1, data=b"test", size=4)

        assert chunk1 != chunk2

    def test_different_data_not_equal(self):
        """Test chunks with different data not equal."""
        chunk1 = FileChunk(index=0, data=b"test", size=4)
        chunk2 = FileChunk(index=0, data=b"diff", size=4)

        assert chunk1 != chunk2


class TestFileChunkEdgeCases:
    """Test edge cases and special scenarios."""

    def test_very_large_chunk(self):
        """Test very large chunk."""
        data = b"x" * 10_000_000  # 10MB
        chunk = FileChunk.create(index=0, data=data)

        assert chunk.size == 10_000_000

    def test_single_byte_chunk(self):
        """Test minimum size chunk."""
        chunk = FileChunk.create(index=0, data=b"x")

        assert chunk.size == 1

    def test_chunk_with_binary_data(self):
        """Test chunk with binary data."""
        binary_data = bytes(range(256))
        chunk = FileChunk.create(index=0, data=binary_data)

        assert chunk.size == 256
        assert chunk.data == binary_data

    def test_chunk_index_very_large(self):
        """Test chunk with very large index."""
        chunk = FileChunk.create(index=999999, data=b"test")

        assert chunk.index == 999999

    def test_chunk_data_contains_nulls(self):
        """Test chunk with null bytes."""
        data = b"hello\x00world\x00"
        chunk = FileChunk.create(index=0, data=data)

        assert chunk.data == data
        assert chunk.size == len(data)

    def test_hash_for_set_usage(self):
        """Test chunks can be used in sets (hashable)."""
        chunk1 = FileChunk(index=0, data=b"test", size=4)
        chunk2 = FileChunk(index=1, data=b"test", size=4)

        chunk_set = {chunk1, chunk2}

        assert len(chunk_set) == 2
