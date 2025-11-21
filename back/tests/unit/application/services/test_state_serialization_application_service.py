"""Tests for StateSerializationApplicationService class."""

import pytest
from unittest.mock import Mock
from app.src.application.services.state_serialization_application_service import StateSerializationApplicationService
from app.src.services.sequence_generator import SequenceGenerator


class TestStateSerializationApplicationService:
    """Test suite for StateSerializationApplicationService class."""

    @pytest.fixture
    def mock_sequences(self):
        """Mock sequence generator."""
        mock = Mock()
        mock.get_current_global_seq.return_value = 100
        mock.get_current_playlist_seq.return_value = 50
        return mock

    @pytest.fixture
    def service(self, mock_sequences):
        """Create StateSerializationApplicationService instance."""
        return StateSerializationApplicationService(mock_sequences)

    def test_init(self, mock_sequences):
        """Test StateSerializationApplicationService initialization."""
        service = StateSerializationApplicationService(mock_sequences)
        assert service.sequences == mock_sequences

    def test_init_with_default_sequences(self):
        """Test initialization with default sequence generator."""
        service = StateSerializationApplicationService()
        assert isinstance(service.sequences, SequenceGenerator)

    def test_serialize_playlist_dict_with_tracks(self, service, mock_sequences):
        """Test playlist serialization from dictionary with tracks."""
        playlist_dict = {
            "id": "playlist_123",
            "title": "Test Playlist",
            "description": "A test playlist",
            "nfc_tag_id": "nfc_456",
            "tracks": [
                {"id": "track_1", "title": "Track 1"},
                {"id": "track_2", "title": "Track 2"}
            ],
            "track_count": 2,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-02T00:00:00Z"
        }

        result = service.serialize_playlist(playlist_dict)

        assert result["id"] == "playlist_123"
        assert result["title"] == "Test Playlist"
        assert result["description"] == "A test playlist"
        assert result["nfc_tag_id"] == "nfc_456"
        assert result["track_count"] == 2
        assert result["created_at"] == "2023-01-01T00:00:00Z"
        assert result["updated_at"] == "2023-01-02T00:00:00Z"
        assert result["server_seq"] == 100
        assert result["playlist_seq"] == 50
        assert len(result["tracks"]) == 2
        assert result["tracks"][0]["id"] == "track_1"

    def test_serialize_playlist_dict_without_tracks(self, service, mock_sequences):
        """Test playlist serialization without tracks."""
        playlist_dict = {
            "id": "playlist_123",
            "title": "Test Playlist",
            "tracks": [{"id": "track_1"}]
        }

        result = service.serialize_playlist(playlist_dict, include_tracks=False)

        assert result["id"] == "playlist_123"
        assert result["title"] == "Test Playlist"
        assert "tracks" not in result
        assert result["server_seq"] == 100

    def test_serialize_playlist_object(self, service, mock_sequences):
        """Test playlist serialization from domain object."""
        # Mock domain object
        playlist_obj = Mock()
        playlist_obj.id = "playlist_456"
        playlist_obj.title = "Object Playlist"
        playlist_obj.description = "From object"
        playlist_obj.nfc_tag_id = "nfc_789"
        playlist_obj.track_count = 3
        playlist_obj.created_at = "2023-01-01T00:00:00Z"
        playlist_obj.updated_at = "2023-01-02T00:00:00Z"
        playlist_obj.tracks = [Mock(id="track_1", title="Track 1")]

        result = service.serialize_playlist(playlist_obj)

        assert result["id"] == "playlist_456"
        assert result["title"] == "Object Playlist"
        assert result["description"] == "From object"
        assert result["nfc_tag_id"] == "nfc_789"
        assert result["track_count"] == 3
        assert result["server_seq"] == 100
        assert result["playlist_seq"] == 50

    def test_serialize_playlist_object_minimal_attributes(self, service, mock_sequences):
        """Test playlist serialization from object with minimal attributes."""
        # Mock domain object with minimal attributes
        playlist_obj = Mock()
        playlist_obj.id = "playlist_minimal"
        playlist_obj.title = "Minimal Playlist"

        # Use side_effect to simulate missing attributes properly
        def side_effect_for_missing_attr(*args, **kwargs):
            raise AttributeError("No such attribute")

        # Remove optional attributes to simulate missing ones
        del playlist_obj.description
        del playlist_obj.nfc_tag_id
        del playlist_obj.track_count
        del playlist_obj.created_at
        del playlist_obj.updated_at
        playlist_obj.tracks = []

        result = service.serialize_playlist(playlist_obj, include_tracks=False)

        assert result["id"] == "playlist_minimal"
        assert result["title"] == "Minimal Playlist"
        assert result["description"] == ""
        assert result["nfc_tag_id"] is None

    def test_serialize_track_dict(self, service, mock_sequences):
        """Test track serialization from dictionary."""
        track_dict = {
            "id": "track_123",
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album"
        }

        result = service.serialize_track(track_dict)

        assert result["id"] == "track_123"
        assert result["title"] == "Test Track"
        assert result["artist"] == "Test Artist"
        assert result["album"] == "Test Album"
        assert result["server_seq"] == 100

    def test_serialize_track_object(self, service, mock_sequences):
        """Test track serialization from domain object."""
        # Mock domain object
        track_obj = Mock()
        track_obj.id = "track_456"
        track_obj.title = "Object Track"
        track_obj.filename = "track.mp3"
        track_obj.duration = 180.5  # 3 minutes 30.5 seconds
        track_obj.artist = "Object Artist"
        track_obj.album = "Object Album"
        track_obj.number = 3
        track_obj.play_count = 42
        track_obj.created_at = "2023-01-01T00:00:00Z"

        result = service.serialize_track(track_obj)

        assert result["id"] == "track_456"
        assert result["title"] == "Object Track"
        assert result["filename"] == "track.mp3"
        assert result["duration_ms"] == 180500  # Converted to milliseconds
        assert result["artist"] == "Object Artist"
        assert result["album"] == "Object Album"
        assert result["track_number"] == 3
        assert result["play_count"] == 42
        assert result["created_at"] == "2023-01-01T00:00:00Z"
        assert result["server_seq"] == 100

    def test_serialize_track_object_minimal_attributes(self, service, mock_sequences):
        """Test track serialization from object with minimal attributes."""
        # Mock domain object with minimal attributes
        track_obj = Mock()
        track_obj.id = "track_minimal"
        track_obj.title = "Minimal Track"
        track_obj.filename = "minimal.mp3"
        track_obj.duration = None
        # Missing optional attributes
        del track_obj.artist
        del track_obj.album

        result = service.serialize_track(track_obj)

        assert result["id"] == "track_minimal"
        assert result["title"] == "Minimal Track"
        assert result["filename"] == "minimal.mp3"
        assert result["duration_ms"] == 0  # None duration becomes 0
        assert result["artist"] is None
        assert result["album"] is None

    def test_serialize_playlists_collection(self, service, mock_sequences):
        """Test serialization of playlists collection."""
        playlists = [
            {"id": "playlist_1", "title": "Playlist 1"},
            {"id": "playlist_2", "title": "Playlist 2"}
        ]

        result = service.serialize_playlists_collection(playlists)

        assert len(result) == 2
        assert result[0]["id"] == "playlist_1"
        assert result[1]["id"] == "playlist_2"
        # Should not include tracks for collection serialization
        assert "tracks" not in result[0]
        assert "tracks" not in result[1]

    def test_serialize_tracks_collection(self, service, mock_sequences):
        """Test serialization of tracks collection."""
        tracks = [
            {"id": "track_1", "title": "Track 1"},
            {"id": "track_2", "title": "Track 2"}
        ]

        result = service.serialize_tracks_collection(tracks)

        assert len(result) == 2
        assert result[0]["id"] == "track_1"
        assert result[1]["id"] == "track_2"
        assert result[0]["server_seq"] == 100
        assert result[1]["server_seq"] == 100

    def test_serialize_playback_state_complete(self, service, mock_sequences):
        """Test complete playback state serialization."""
        track_info = {"id": "track_123", "title": "Current Track"}
        playlist_info = {"id": "playlist_456", "title": "Current Playlist"}

        result = service.serialize_playback_state(
            state="playing",
            track_info=track_info,
            playlist_info=playlist_info,
            position=30.5,
            volume=75,
            error="Some error"
        )

        assert result["state"] == "playing"
        assert result["position_seconds"] == 30.5
        assert result["volume"] == 75
        assert result["server_seq"] == 100
        assert result["timestamp"] == 100  # Uses seq as timestamp reference
        assert result["track"] == track_info
        assert result["playlist"] == playlist_info
        assert result["error"] == "Some error"

    def test_serialize_playback_state_minimal(self, service, mock_sequences):
        """Test minimal playback state serialization."""
        result = service.serialize_playback_state("stopped")

        assert result["state"] == "stopped"
        assert result["position_seconds"] == 0.0
        assert result["volume"] == 50
        assert result["server_seq"] == 100
        assert "track" not in result
        assert "playlist" not in result
        assert "error" not in result

    def test_serialize_playback_state_with_partial_info(self, service, mock_sequences):
        """Test playback state serialization with partial information."""
        track_info = {"id": "track_123", "title": "Current Track"}

        result = service.serialize_playback_state(
            state="paused",
            track_info=track_info,
            position=120.0,
            volume=60
        )

        assert result["state"] == "paused"
        assert result["position_seconds"] == 120.0
        assert result["volume"] == 60
        assert result["track"] == track_info
        assert "playlist" not in result
        assert "error" not in result