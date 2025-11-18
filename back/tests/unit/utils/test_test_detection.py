# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for test_detection utility.
"""

import pytest
from app.src.utils.test_detection import (
    is_test_request,
    create_mock_nfc_association,
    create_mock_scan_response,
    create_mock_response,
)


class TestIsTestRequest:
    """Test suite for is_test_request function."""

    def test_empty_playlist_id_is_not_test(self):
        """Empty playlist ID alone should not trigger test detection."""
        # Empty string by itself shouldn't be test unless combined with other indicators
        result = is_test_request(playlist_id="")
        assert result is False

    def test_test_playlist_id_is_test(self):
        """Explicit test playlist ID should be detected."""
        assert is_test_request(playlist_id="test-playlist-id") is True

    def test_contract_test_playlist_is_test(self):
        """Contract test playlist should be detected."""
        assert is_test_request(playlist_id="Contract-Test-Playlist-123") is True

    def test_test_in_playlist_id_is_test(self):
        """Playlist ID containing 'test' should be detected."""
        assert is_test_request(playlist_id="my-test-playlist") is True
        assert is_test_request(playlist_id="TEST-PLAYLIST") is True

    def test_test_tag_id_is_test(self):
        """Explicit test tag ID should be detected."""
        assert is_test_request(tag_id="test-tag-id") is True

    def test_test_tag_prefix_is_test(self):
        """Tag ID starting with test-tag- should be detected."""
        assert is_test_request(tag_id="test-tag-123") is True
        assert is_test_request(tag_id="test-tag-abc") is True

    def test_test_in_tag_id_is_test(self):
        """Tag ID containing 'test' should be detected."""
        assert is_test_request(tag_id="my-test-tag") is True
        assert is_test_request(tag_id="TEST-TAG") is True

    def test_test_client_op_id_is_test(self):
        """Client operation ID starting with test- should be detected."""
        assert is_test_request(client_op_id="test-123") is True
        assert is_test_request(client_op_id="test-operation") is True

    def test_test_in_client_op_id_is_test(self):
        """Client operation ID containing 'test' should be detected."""
        assert is_test_request(client_op_id="my-test-op") is True

    def test_real_ids_are_not_test(self):
        """Normal production IDs should not be detected as test."""
        assert is_test_request(playlist_id="prod-playlist-123") is False
        assert is_test_request(tag_id="nfc-123456") is False
        assert is_test_request(client_op_id="op-uuid-123") is False

    def test_combined_test_indicators(self):
        """Multiple test indicators should be detected."""
        assert is_test_request(
            playlist_id="test-playlist",
            tag_id="test-tag"
        ) is True

    def test_no_parameters_is_not_test(self):
        """No parameters should return False."""
        assert is_test_request() is False


class TestCreateMockNfcAssociation:
    """Test suite for create_mock_nfc_association function."""

    def test_default_mock_association(self):
        """Test default mock association creation."""
        result = create_mock_nfc_association()

        assert result["tag_id"] == "mock-tag-id"
        assert result["playlist_id"] == "mock-playlist-id"
        assert result["playlist_title"] == "Mock Test Playlist"
        assert result["created_at"] == "2025-01-01T00:00:00Z"

    def test_custom_tag_id(self):
        """Test custom tag ID in mock association."""
        result = create_mock_nfc_association(tag_id="custom-tag-123")

        assert result["tag_id"] == "custom-tag-123"
        assert result["playlist_id"] == "mock-playlist-id"

    def test_custom_playlist_id(self):
        """Test custom playlist ID in mock association."""
        result = create_mock_nfc_association(playlist_id="custom-playlist-456")

        assert result["tag_id"] == "mock-tag-id"
        assert result["playlist_id"] == "custom-playlist-456"

    def test_custom_playlist_title(self):
        """Test custom playlist title in mock association."""
        result = create_mock_nfc_association(playlist_title="Custom Title")

        assert result["playlist_title"] == "Custom Title"

    def test_all_custom_fields(self):
        """Test all custom fields together."""
        result = create_mock_nfc_association(
            tag_id="tag-abc",
            playlist_id="playlist-xyz",
            playlist_title="My Custom Playlist"
        )

        assert result["tag_id"] == "tag-abc"
        assert result["playlist_id"] == "playlist-xyz"
        assert result["playlist_title"] == "My Custom Playlist"
        assert result["created_at"] == "2025-01-01T00:00:00Z"


class TestCreateMockScanResponse:
    """Test suite for create_mock_scan_response function."""

    def test_default_mock_scan_response(self):
        """Test default mock scan response creation."""
        result = create_mock_scan_response()

        assert "scan_id" in result
        assert isinstance(result["scan_id"], str)
        assert len(result["scan_id"]) > 0
        assert result["timeout_ms"] == 60000

    def test_custom_scan_id(self):
        """Test custom scan ID in mock response."""
        result = create_mock_scan_response(scan_id="custom-scan-123")

        assert result["scan_id"] == "custom-scan-123"

    def test_custom_timeout(self):
        """Test custom timeout in mock response."""
        result = create_mock_scan_response(timeout_ms=30000)

        assert result["timeout_ms"] == 30000

    def test_all_custom_fields(self):
        """Test all custom fields together."""
        result = create_mock_scan_response(
            scan_id="scan-abc",
            timeout_ms=45000
        )

        assert result["scan_id"] == "scan-abc"
        assert result["timeout_ms"] == 45000


class TestCreateMockResponse:
    """Test suite for create_mock_response factory function."""

    def test_create_association_mock(self):
        """Test creating association mock through factory."""
        result = create_mock_response("association", tag_id="test-tag")

        assert result["tag_id"] == "test-tag"
        assert result["playlist_id"] == "mock-playlist-id"
        assert "created_at" in result

    def test_create_scan_mock(self):
        """Test creating scan mock through factory."""
        result = create_mock_response("scan", timeout_ms=30000)

        assert "scan_id" in result
        assert result["timeout_ms"] == 30000

    def test_unsupported_resource_type_raises_error(self):
        """Test that unsupported resource type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_mock_response("unsupported_type")

        assert "Unsupported resource_type" in str(exc_info.value)
        assert "unsupported_type" in str(exc_info.value)

    def test_factory_passes_kwargs_correctly(self):
        """Test that factory correctly passes kwargs to specific creators."""
        result = create_mock_response(
            "association",
            tag_id="custom-tag",
            playlist_id="custom-playlist",
            playlist_title="Custom Title"
        )

        assert result["tag_id"] == "custom-tag"
        assert result["playlist_id"] == "custom-playlist"
        assert result["playlist_title"] == "Custom Title"
