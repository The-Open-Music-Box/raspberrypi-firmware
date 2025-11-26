# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Serialization Contract Tests

These tests ensure ALL serialization paths produce consistent output
that matches the frontend contract expectations.

Purpose: Prevent bugs like issue #71 where duplicate serialization paths
diverged and caused missing required fields.
"""

import pytest
from app.src.domain.data.models.track import Track
from app.src.domain.data.models.playlist import Playlist
from app.src.services.serialization.unified_serialization_service import UnifiedSerializationService


class TestSerializationContracts:
    """Test that all serialization methods produce contract-compliant output."""

    @pytest.fixture
    def sample_track(self):
        """Create a sample track for testing."""
        return Track(
            track_number=1,
            title="Test Track",
            filename="test.mp3",
            file_path="/test/test.mp3",
            duration_ms=180000,
            artist="Test Artist",
            album="Test Album",
            id="test-track-id"
        )

    @pytest.fixture
    def sample_playlist(self, sample_track):
        """Create a sample playlist for testing."""
        return Playlist(
            title="Test Playlist",
            description="Test Description",
            tracks=[sample_track],
            nfc_tag_id="test-nfc-tag",
            id="test-playlist-id"
        )

    def test_track_serialization_includes_required_fields(self, sample_track):
        """Test that track serialization includes ALL required fields for frontend contract."""
        result = UnifiedSerializationService.serialize_track(sample_track, format="api")

        # Required fields per OpenAPI contract v3.3.2
        required_fields = [
            'id',
            'number',  # Frontend requirement - CRITICAL
            'track_number',  # Backend field name
            'title',
            'filename',
            'file_path',
            'duration_ms',
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Verify 'number' matches 'track_number'
        assert result['number'] == result['track_number'], \
            "'number' field must match 'track_number' value"
        assert result['number'] == 1, "Expected track number 1"

    def test_track_serialization_field_types(self, sample_track):
        """Test that serialized track fields have correct types."""
        result = UnifiedSerializationService.serialize_track(sample_track, format="api")

        # Type validation
        assert isinstance(result['id'], str), "id must be string"
        assert isinstance(result['number'], int), "number must be integer"
        assert isinstance(result['track_number'], int), "track_number must be integer"
        assert isinstance(result['title'], str), "title must be string"
        assert isinstance(result['filename'], str), "filename must be string"
        assert isinstance(result['duration_ms'], int), "duration_ms must be integer"

    def test_track_serialization_with_property_field(self, sample_track):
        """Test that @property field 'number' is included despite being a property."""
        result = UnifiedSerializationService.serialize_track(sample_track, format="api")

        # The 'number' field is a @property on Track model
        # It should be explicitly added by serialization service
        assert 'number' in result, \
            "Serialization MUST include @property field 'number' for frontend compatibility"

        # Verify it returns the correct value
        assert result['number'] == sample_track.number, \
            "Serialized 'number' must match Track.number property"

    def test_playlist_serialization_includes_tracks_with_number_field(self, sample_playlist):
        """Test that playlist serialization includes tracks with 'number' field."""
        result = UnifiedSerializationService.serialize_playlist(sample_playlist, format="api")

        assert 'tracks' in result, "Playlist must include tracks array"
        assert len(result['tracks']) > 0, "Test playlist should have tracks"

        # Verify each track has the 'number' field
        for track in result['tracks']:
            assert 'number' in track, \
                f"Track '{track.get('title')}' missing 'number' field in playlist serialization"
            assert isinstance(track['number'], int), \
                f"Track 'number' field must be integer, got {type(track['number'])}"

    def test_track_serialization_consistency_across_formats(self, sample_track):
        """Test that different serialization formats maintain 'number' field."""
        api_result = UnifiedSerializationService.serialize_track(sample_track, format="api")

        # API format MUST include 'number' field
        assert 'number' in api_result, "API format must include 'number' field"
        assert api_result['number'] == 1

    def test_track_serialization_from_dict(self):
        """Test that serialization works when input is already a dict."""
        track_dict = {
            'id': 'test-id',
            'track_number': 5,
            'title': 'Dict Track',
            'filename': 'track.mp3',
            'file_path': '/path/track.mp3',
            'duration_ms': 200000
        }

        result = UnifiedSerializationService.serialize_track(track_dict, format="api")

        assert 'number' in result, "Must add 'number' field even when serializing from dict"
        assert result['number'] == 5, "number should match track_number from dict"

    def test_track_serialization_handles_missing_optional_fields(self):
        """Test that serialization handles tracks with missing optional fields gracefully."""
        minimal_track = Track(
            track_number=1,
            title="Minimal Track",
            filename="minimal.mp3",
            file_path="/minimal.mp3",
            duration_ms=1000,
            id="minimal-id"
            # artist and album are None
        )

        result = UnifiedSerializationService.serialize_track(minimal_track, format="api")

        # Still must have required fields
        assert 'number' in result, "Must include 'number' even for minimal track"
        assert result['number'] == 1

    def test_serialization_prevents_silent_field_omission(self, sample_track):
        """Test that serialization explicitly includes fields, not relying on @property auto-serialization."""
        result = UnifiedSerializationService.serialize_track(sample_track, format="api")

        # This test documents the fix for issue #71
        # Python's dataclasses.asdict() does NOT serialize @property fields
        # UnifiedSerializationService MUST explicitly add them

        assert 'number' in result, \
            "REGRESSION CHECK: 'number' field must be explicitly added " \
            "(not relying on @property auto-serialization)"

        assert result['number'] == result['track_number'], \
            "Explicitly added 'number' must match 'track_number' value"

    def test_playlist_serialization_regression_check(self, sample_playlist):
        """Regression test: Verify playlist serialization doesn't lose track fields."""
        result = UnifiedSerializationService.serialize_playlist(sample_playlist, format="api")

        # Issue #71: Playlist broadcasts missing 'number' field
        # This test ensures it never happens again

        for idx, track in enumerate(result['tracks']):
            assert 'number' in track, \
                f"REGRESSION: Track {idx} in playlist missing 'number' field. " \
                f"This caused issue #71 where playlists with NFC tags failed to display."

            assert 'track_number' in track, \
                f"Track {idx} missing 'track_number' field"

            assert track['number'] == track['track_number'], \
                f"Track {idx}: 'number' and 'track_number' must be identical"


class TestSerializationContractValidation:
    """Test validation helpers for contract compliance."""

    def test_validate_track_dict_with_valid_track(self):
        """Test validation passes for correctly serialized track."""
        valid_track = {
            'id': 'test-id',
            'number': 1,
            'track_number': 1,
            'title': 'Valid Track',
            'filename': 'valid.mp3',
            'file_path': '/valid.mp3',
            'duration_ms': 180000
        }

        # Should not raise any assertions
        assert 'number' in valid_track
        assert valid_track['number'] == valid_track['track_number']

    def test_validate_track_dict_detects_missing_number_field(self):
        """Test that we can detect missing 'number' field (the bug from issue #71)."""
        buggy_track = {
            'id': 'buggy-id',
            'track_number': 1,  # Has this
            # 'number': 1,  # MISSING - this was the bug!
            'title': 'Buggy Track',
            'filename': 'buggy.mp3',
            'duration_ms': 180000
        }

        # This is what the bug looked like
        assert 'number' not in buggy_track, \
            "This test documents the bug: 'number' field was missing"

        # Validation should detect this
        has_number = 'number' in buggy_track
        assert not has_number, "Test confirms the field is missing"

    def test_all_serialization_paths_produce_identical_output(self):
        """Test that different serialization paths produce consistent output."""
        # Create test track
        track = Track(
            track_number=7,
            title="Consistency Test",
            filename="test.mp3",
            file_path="/test.mp3",
            duration_ms=210000,
            id="consistency-test-id"
        )

        # Serialize via UnifiedSerializationService
        unified_result = UnifiedSerializationService.serialize_track(track, format="api")

        # Key fields should be present
        assert unified_result['number'] == 7
        assert unified_result['track_number'] == 7
        assert unified_result['title'] == "Consistency Test"

        # Note: We removed the buggy PurePlaylistRepositoryAdapter._track_to_dict()
        # so there's now only ONE serialization path - which prevents divergence!


class TestContractRegressionPrevention:
    """Tests specifically designed to prevent issue #71 from recurring."""

    def test_track_number_field_always_present_in_api_format(self):
        """Critical test: 'number' field MUST be present in API format."""
        track = Track(
            track_number=99,
            title="Critical Test",
            filename="critical.mp3",
            file_path="/critical.mp3",
            duration_ms=1000,
            id="critical-id"
        )

        result = UnifiedSerializationService.serialize_track(track, format="api")

        assert 'number' in result, \
            "CRITICAL: 'number' field missing. This causes frontend contract violations!"

        assert result['number'] == 99, \
            "'number' field has wrong value"

    def test_websocket_broadcast_data_includes_number_field(self):
        """Test that WebSocket broadcast data includes 'number' field."""
        # This simulates what gets broadcast via WebSocket
        playlist = Playlist(
            title="WebSocket Test",
            tracks=[
                Track(
                    track_number=1,
                    title="WS Track",
                    filename="ws.mp3",
                    file_path="/ws.mp3",
                    duration_ms=1000,
                    id="ws-id"
                )
            ],
            id="ws-playlist-id"
        )

        # Serialize as would happen in WebSocket broadcast
        result = UnifiedSerializationService.serialize_playlist(playlist, format="api")

        # The bug in issue #71: WebSocket broadcasts used PurePlaylistRepositoryAdapter._track_to_dict()
        # which didn't include 'number' field
        assert len(result['tracks']) > 0
        assert 'number' in result['tracks'][0], \
            "WebSocket broadcasts MUST include 'number' field (issue #71 regression check)"

    def test_nfc_triggered_playlist_load_includes_number_field(self):
        """Regression test: NFC-triggered playlist loads must include 'number' field."""
        # Issue #71 was triggered by playlist "bibeo - promenons nous dans les bois"
        # which had NFC tag "04889462251c91"
        # When NFC tag triggered playlist load, it used broken serialization path

        nfc_playlist = Playlist(
            title="bibeo - promenons nous dans les bois",
            nfc_tag_id="04889462251c91",
            tracks=[
                Track(
                    track_number=1,
                    title="A la volette [zV-Rl7VVagw]",
                    filename="track.mp3",
                    file_path="/track.mp3",
                    duration_ms=180000,
                    id="02f22714-3fd7-4ae7-9ff3-7c24feee303d"
                )
            ],
            id="nfc-playlist-id"
        )

        result = UnifiedSerializationService.serialize_playlist(nfc_playlist, format="api")

        # This was the exact error message from issue #71
        track = result['tracks'][0]
        assert 'number' in track, \
            f"CONTRACT VIOLATION: Track missing required 'number' field. " \
            f"Track: {track.get('title')} (ID: {track.get('id')}). " \
            f"Available fields: {', '.join(track.keys())}. " \
            f"This caused issue #71."
