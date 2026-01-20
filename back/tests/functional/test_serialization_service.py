#!/usr/bin/env python3
"""
Functional tests for the UnifiedSerializationService.

Tests the complete serialization workflow including:
1. Playlist serialization with various data types
2. Track serialization with None handling
3. Different output formats (API, WebSocket, Database)
4. Error handling for malformed data
"""

import pytest
from typing import Dict, Any, List
from app.src.services.serialization.unified_serialization_service import UnifiedSerializationService


class TestUnifiedSerializationService:
    """Test suite for UnifiedSerializationService functionality."""

    def test_serialize_playlist_handles_none_duration(self):
        """Test that playlist serialization handles None duration_ms values correctly."""
        # Create playlist with tracks having None duration_ms
        playlist_data = {
            "id": "test-playlist-123",
            "title": "Test Playlist",
            "description": "Test description",
            "nfc_tag_id": None,
            "tracks": [
                {
                    "id": "track-1",
                    "track_number": 1,
                    "title": "Track 1",
                    "filename": "track1.mp3",
                    "duration_ms": None,  # This should not cause TypeError
                    "artist": "Test Artist",
                    "album": "Test Album"
                },
                {
                    "id": "track-2",
                    "track_number": 2,
                    "title": "Track 2",
                    "filename": "track2.mp3",
                    "duration_ms": 120000,  # Valid duration
                    "artist": "Test Artist",
                    "album": "Test Album"
                },
                {
                    "id": "track-3",
                    "track_number": 3,
                    "title": "Track 3",
                    "filename": "track3.mp3",
                    "duration_ms": 0,  # Zero duration
                    "artist": None,
                    "album": None
                }
            ]
        }

        # Should not raise TypeError
        result = UnifiedSerializationService.serialize_playlist(
            playlist_data,
            include_tracks=True,
            calculate_duration=True
        )

        # Verify result structure
        assert result["id"] == "test-playlist-123"
        assert result["title"] == "Test Playlist"
        assert len(result["tracks"]) == 3

        # Verify duration calculation handles None values
        assert "total_duration_ms" in result
        assert result["total_duration_ms"] == 120000  # Only track 2 has valid duration
        assert result["track_count"] == 3

        # Verify individual track duration handling
        track_1 = result["tracks"][0]
        assert track_1["duration_ms"] == 0  # None should be converted to 0

        track_2 = result["tracks"][1]
        assert track_2["duration_ms"] == 120000  # Should remain unchanged

        track_3 = result["tracks"][2]
        assert track_3["duration_ms"] == 0  # Should remain 0

    def test_serialize_track_handles_none_values(self):
        """Test that track serialization handles None values correctly."""
        track_data = {
            "id": "track-test",
            "track_number": 1,
            "title": "Test Track",
            "filename": "test.mp3",
            "duration_ms": None,  # Should be converted to 0
            "artist": None,
            "album": None
        }

        result = UnifiedSerializationService.serialize_track(track_data)

        assert result["duration_ms"] == 0
        assert result["artist"] is None
        assert result["album"] is None
        assert result["title"] == "Test Track"

    def test_serialize_playlist_different_formats(self):
        """Test playlist serialization in different formats."""
        playlist_data = {
            "id": "format-test",
            "title": "Format Test Playlist",
            "description": "Testing different formats",
            "nfc_tag_id": "nfc-123",
            "path": "format_test_playlist",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T12:00:00",
            "tracks": [
                {
                    "id": "track-1",
                    "track_number": 1,
                    "title": "Test Track",
                    "duration_ms": 180000
                }
            ]
        }

        # Test API format
        api_result = UnifiedSerializationService.serialize_playlist(
            playlist_data, format=UnifiedSerializationService.FORMAT_API
        )
        assert "created_at" in api_result
        assert "updated_at" in api_result
        assert api_result["created_at"] == "2025-01-01T00:00:00"

        # Test WebSocket format
        ws_result = UnifiedSerializationService.serialize_playlist(
            playlist_data, format=UnifiedSerializationService.FORMAT_WEBSOCKET
        )
        assert ws_result["type"] == "playlist"
        assert "created_at" not in ws_result  # Websocket format is more compact

        # Test Database format
        db_result = UnifiedSerializationService.serialize_playlist(
            playlist_data, format=UnifiedSerializationService.FORMAT_DATABASE
        )
        assert "path" in db_result
        assert db_result["path"] == "format_test_playlist"

        # Test Internal format
        internal_result = UnifiedSerializationService.serialize_playlist(
            playlist_data, format=UnifiedSerializationService.FORMAT_INTERNAL
        )
        assert "path" in internal_result
        assert internal_result["path"] == "format_test_playlist"

    def test_serialize_bulk_playlists(self):
        """Test bulk playlist serialization."""
        playlists_data = [
            {
                "id": "playlist-1",
                "title": "Playlist 1",
                "tracks": [{"id": "t1", "duration_ms": 120000}]
            },
            {
                "id": "playlist-2",
                "title": "Playlist 2",
                "tracks": [{"id": "t2", "duration_ms": None}, {"id": "t3", "duration_ms": 90000}]
            }
        ]

        result = UnifiedSerializationService.serialize_bulk_playlists(
            playlists_data, include_tracks=True
        )

        assert len(result) == 2
        assert result[0]["id"] == "playlist-1"
        assert result[0]["total_duration_ms"] == 120000

        assert result[1]["id"] == "playlist-2"
        assert result[1]["total_duration_ms"] == 90000  # None duration should not break calculation

    def test_serialize_domain_entity(self):
        """Test serialization of domain entities with attributes."""
        # Mock domain entity class
        class MockPlaylist:
            def __init__(self):
                self.id = "domain-playlist"
                self.name = "Domain Playlist"
                self.description = "From domain entity"
                self.nfc_tag_id = None
                self.tracks = []

        domain_playlist = MockPlaylist()
        result = UnifiedSerializationService.serialize_playlist(domain_playlist)

        assert result["id"] == "domain-playlist"
        assert result["title"] == "Domain Playlist"  # name -> title mapping
        assert result["description"] == "From domain entity"

    def test_serialize_database_row(self):
        """Test serialization of database row tuples."""
        # Mock database row (tuple format)
        db_row = (
            "db-playlist-id",
            "DB Playlist Title",
            "DB Description",
            "nfc-tag-456",
            "2025-01-01T00:00:00",
            "2025-01-01T12:00:00"
        )

        result = UnifiedSerializationService.serialize_playlist(db_row, include_tracks=False)

        assert result["id"] == "db-playlist-id"
        assert result["title"] == "DB Playlist Title"
        assert result["description"] == "DB Description"
        assert result["nfc_tag_id"] == "nfc-tag-456"

    def test_serialize_empty_or_none_playlist(self):
        """Test handling of empty or None playlist data."""
        # Test None playlist
        result = UnifiedSerializationService.serialize_playlist(None)
        assert result["id"] is None
        assert result["title"] == ""
        assert result["tracks"] == []

        # Test empty dict
        result = UnifiedSerializationService.serialize_playlist({})
        assert result["id"] is None
        assert result["title"] == ""
        assert result["tracks"] == []

    def test_format_context_mapping(self):
        """Test format determination from context strings."""
        assert UnifiedSerializationService.get_format_for_context("route") == "api"
        assert UnifiedSerializationService.get_format_for_context("API") == "api"
        assert UnifiedSerializationService.get_format_for_context("websocket") == "websocket"
        assert UnifiedSerializationService.get_format_for_context("SOCKET") == "websocket"
        assert UnifiedSerializationService.get_format_for_context("database") == "database"
        assert UnifiedSerializationService.get_format_for_context("DB") == "database"
        assert UnifiedSerializationService.get_format_for_context("internal") == "internal"
        assert UnifiedSerializationService.get_format_for_context("DOMAIN") == "internal"
        assert UnifiedSerializationService.get_format_for_context("unknown") == "api"  # Default