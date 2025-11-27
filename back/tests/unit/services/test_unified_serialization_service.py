# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for UnifiedSerializationService

Tests the critical serialization logic that converts domain entities to API responses.
These tests prevent field mismatches between backend and frontend (issue #71).
"""

import pytest
from app.src.domain.data.models.track import Track
from app.src.domain.data.models.playlist import Playlist
from app.src.services.serialization.unified_serialization_service import (
    UnifiedSerializationService,
)


class TestTrackSerialization:
    """Test Track serialization to prevent frontend contract violations."""

    def test_serialize_track_api_format_includes_number_field(self):
        """
        CRITICAL TEST: Verify 'number' field exists in API format.

        This test prevents issue #71 where frontend expected 'number' field
        but received only 'number', causing all tracks to default to 0.
        """
        track = Track(
            id="test-track-id",
            track_number=5,
            title="Test Track",
            filename="test.mp3",
            file_path="/path/to/test.mp3",
            duration_ms=180000,
            artist="Test Artist",
            album="Test Album"
        )

        result = UnifiedSerializationService.serialize_track(
            track,
            format=UnifiedSerializationService.FORMAT_API
        )

        # CRITICAL: Verify 'number' field exists (per OpenAPI contract v3.3.2)
        assert "number" in result, (
            f"Track serialization missing 'number' field. "
            f"Available fields: {list(result.keys())}"
        )
        assert result["number"] == 5, "number field should match track position"

        # Per OpenAPI contract v3.3.2, only 'number' field should exist
        assert "number" not in result, (
            "track_number field should not exist - use 'number' per OpenAPI contract"
        )

    def test_serialize_track_api_format_all_required_fields(self):
        """Verify all required fields are present in API format."""
        track = Track(
            id="test-id",
            track_number=3,
            title="Track Title",
            filename="track.mp3",
            file_path="/path/track.mp3",
            duration_ms=240000
        )

        result = UnifiedSerializationService.serialize_track(
            track,
            format=UnifiedSerializationService.FORMAT_API
        )

        # Required fields per OpenAPI contract v3.3.2 and frontend Track interface
        required_fields = [
            "id",
            "number",  # Per OpenAPI contract v3.3.2
            "title",
            "filename",
            "duration_ms",
            "file_path",
            "created_at",
            "updated_at",
            "server_seq"
        ]

        missing_fields = [f for f in required_fields if f not in result]
        assert not missing_fields, f"Missing required fields: {missing_fields}"

    def test_serialize_track_number_never_zero_for_valid_tracks(self):
        """
        Verify track_number is never 0 in serialization.

        In issue #71, all tracks had number=0 due to missing field,
        causing deletion to remove all tracks.
        """
        track = Track(
            id="test-id",
            track_number=1,
            title="First Track",
            filename="first.mp3",
            file_path="/path/first.mp3"
        )

        result = UnifiedSerializationService.serialize_track(
            track,
            format=UnifiedSerializationService.FORMAT_API
        )

        assert result["number"] > 0, "Track number should never be 0 for valid tracks"

    def test_serialize_track_websocket_format(self):
        """Verify WebSocket format is minimal and compact."""
        track = Track(
            id="test-id",
            track_number=2,
            title="Track 2",
            filename="track2.mp3",
            file_path="/path/track2.mp3",
            duration_ms=200000
        )

        result = UnifiedSerializationService.serialize_track(
            track,
            format=UnifiedSerializationService.FORMAT_WEBSOCKET
        )

        # WebSocket format should be minimal (per OpenAPI contract v3.3.2)
        expected_fields = {"id", "number", "title", "duration_ms"}
        assert set(result.keys()) == expected_fields

    def test_serialize_track_from_dict(self):
        """Verify serialization works with dict input (repository layer)."""
        track_dict = {
            "id": "dict-track-id",
            "number": 7,
            "title": "Dict Track",
            "filename": "dict.mp3",
            "file_path": "/path/dict.mp3",
            "duration_ms": 150000
        }

        result = UnifiedSerializationService.serialize_track(
            track_dict,
            format=UnifiedSerializationService.FORMAT_API
        )

        assert "number" in result
        assert result["number"] == 7


class TestPlaylistSerialization:
    """Test Playlist serialization."""

    def test_serialize_playlist_with_tracks_includes_number_field(self):
        """Verify tracks in playlist have 'number' field."""
        track1 = Track(
            id="track-1",
            track_number=1,
            title="Track 1",
            filename="track1.mp3",
            file_path="/path/track1.mp3"
        )
        track2 = Track(
            id="track-2",
            track_number=2,
            title="Track 2",
            filename="track2.mp3",
            file_path="/path/track2.mp3"
        )

        playlist = Playlist(
            id="playlist-id",
            title="Test Playlist",
            description="Test Description",
            tracks=[track1, track2]
        )

        result = UnifiedSerializationService.serialize_playlist(
            playlist,
            include_tracks=True,
            format=UnifiedSerializationService.FORMAT_API
        )

        # Verify all tracks have 'number' field
        assert len(result["tracks"]) == 2
        for track in result["tracks"]:
            assert "number" in track, (
                f"Track in playlist missing 'number' field: {track.keys()}"
            )
            assert track["number"] > 0

    def test_serialize_playlist_track_numbers_are_sequential(self):
        """Verify track numbers are preserved correctly."""
        tracks = [
            Track(
                id=f"track-{i}",
                track_number=i,
                title=f"Track {i}",
                filename=f"track{i}.mp3",
                file_path=f"/path/track{i}.mp3"
            )
            for i in range(1, 6)  # Tracks 1-5
        ]

        playlist = Playlist(
            id="playlist-id",
            title="Sequential Playlist",
            description="",
            tracks=tracks
        )

        result = UnifiedSerializationService.serialize_playlist(
            playlist,
            include_tracks=True,
            format=UnifiedSerializationService.FORMAT_API
        )

        # Verify track numbers are 1, 2, 3, 4, 5
        track_numbers = [track["number"] for track in result["tracks"]]
        assert track_numbers == [1, 2, 3, 4, 5]


class TestContractCompliance:
    """
    Test contract compliance to prevent frontend/backend mismatches.

    These tests ensure the serialization service maintains the contract
    expected by frontend components.
    """

    def test_track_serialization_contract_compliance(self):
        """
        Verify Track serialization matches frontend expectations.

        Frontend expects these fields in Track interface:
        - id: string
        - number: number (NOT track_number!)
        - title: string
        - filename: string
        - duration_ms: number
        """
        track = Track(
            id="contract-test-id",
            track_number=10,
            title="Contract Test",
            filename="contract.mp3",
            file_path="/path/contract.mp3",
            duration_ms=300000
        )

        result = UnifiedSerializationService.serialize_track(
            track,
            format=UnifiedSerializationService.FORMAT_API
        )

        # Frontend contract requirements
        assert isinstance(result["id"], str)
        assert isinstance(result["number"], int)  # Frontend expects 'number'
        assert isinstance(result["title"], str)
        assert isinstance(result["filename"], str)
        assert isinstance(result["duration_ms"], int)

        # Track number must be valid (> 0)
        assert result["number"] > 0

    def test_no_silent_defaults_in_serialization(self):
        """
        Verify serialization doesn't use silent defaults for critical fields.

        Issue #71 was masked by frontend using `?? 0` default.
        Backend should provide explicit values, not rely on frontend defaults.
        """
        track = Track(
            id="explicit-test",
            track_number=15,
            title="Explicit Values",
            filename="explicit.mp3",
            file_path="/path/explicit.mp3"
        )

        result = UnifiedSerializationService.serialize_track(
            track,
            format=UnifiedSerializationService.FORMAT_API
        )

        # Critical fields must have explicit values, not None or 0
        assert result["number"] is not None
        assert result["number"] != 0
        assert result["number"] is not None
        assert result["number"] != 0
