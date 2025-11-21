# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for PlaylistOperationsService (DDD Architecture)

Comprehensive tests for the playlist operations service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.src.api.services.playlist_operations_service import PlaylistOperationsService


class TestPlaylistOperationsService:
    """Test suite for PlaylistOperationsService."""

    @pytest.fixture
    def mock_playlist_app_service(self):
        """Mock playlist application service."""
        service = Mock()
        service.get_playlists_use_case = AsyncMock()
        service.get_playlist_use_case = AsyncMock()
        return service

    @pytest.fixture
    def mock_repository_adapter(self):
        """Mock repository adapter."""
        adapter = Mock()
        adapter.get_playlist_by_id = AsyncMock()
        adapter.update_track_numbers = AsyncMock()
        adapter.replace_tracks = AsyncMock()
        adapter.update_playlist = AsyncMock()
        adapter.delete_playlist = AsyncMock()
        return adapter

    @pytest.fixture
    def operations_service(self, mock_playlist_app_service, mock_repository_adapter):
        """Create PlaylistOperationsService instance."""
        return PlaylistOperationsService(
            playlist_app_service=mock_playlist_app_service,
            repository_adapter=mock_repository_adapter
        )

    @pytest.mark.asyncio
    async def test_reorder_tracks_use_case_success(self, operations_service, mock_repository_adapter):
        """Test successful track reordering."""
        # Arrange
        playlist_id = "test-playlist"
        track_order = [3, 1, 2]
        mock_playlist_data = {
            "id": playlist_id,
            "tracks": [
                {"id": "t1", "track_number": 1, "title": "Track 1", "filename": "track1.mp3", "file_path": "/path/t1"},
                {"id": "t2", "track_number": 2, "title": "Track 2", "filename": "track2.mp3", "file_path": "/path/t2"},
                {"id": "t3", "track_number": 3, "title": "Track 3", "filename": "track3.mp3", "file_path": "/path/t3"},
            ]
        }
        mock_repository_adapter.get_playlist_by_id.return_value = mock_playlist_data
        mock_repository_adapter.update_track_numbers.return_value = True

        with patch("app.src.domain.services.track_reordering_service.TrackReorderingService") as mock_service:
            mock_reordering_service = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.affected_tracks = [
                Mock(id="t3", track_number=1),
                Mock(id="t1", track_number=2),
                Mock(id="t2", track_number=3),
            ]
            mock_reordering_service.execute_reordering.return_value = mock_result
            mock_service.return_value = mock_reordering_service

            # Act
            result = await operations_service.reorder_tracks_use_case(playlist_id, track_order)

            # Assert
            assert result["status"] == "success"
            assert result["playlist_id"] == playlist_id
            mock_repository_adapter.get_playlist_by_id.assert_called_once_with(playlist_id)
            mock_repository_adapter.update_track_numbers.assert_called_once()

    @pytest.mark.asyncio
    async def test_reorder_tracks_playlist_not_found(self, operations_service, mock_repository_adapter):
        """Test track reordering when playlist not found."""
        # Arrange
        playlist_id = "non-existent"
        track_order = [3, 1, 2]
        mock_repository_adapter.get_playlist_by_id.return_value = None

        # Act
        result = await operations_service.reorder_tracks_use_case(playlist_id, track_order)

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_reorder_tracks_validation_failure(self, operations_service, mock_repository_adapter):
        """Test track reordering with validation failure."""
        # Arrange
        playlist_id = "test-playlist"
        track_order = [3, 1, 2]
        mock_playlist_data = {
            "id": playlist_id,
            "tracks": [
                {"id": "t1", "track_number": 1, "title": "Track 1", "filename": "track1.mp3", "file_path": "/path/t1"},
            ]
        }
        mock_repository_adapter.get_playlist_by_id.return_value = mock_playlist_data

        with patch("app.src.domain.services.track_reordering_service.TrackReorderingService") as mock_service:
            mock_reordering_service = Mock()
            mock_result = Mock()
            mock_result.success = False
            mock_result.validation_errors = ["Invalid track order"]
            mock_result.business_rule_violations = ["Business rule violated"]
            mock_reordering_service.execute_reordering.return_value = mock_result
            mock_service.return_value = mock_reordering_service

            # Act
            result = await operations_service.reorder_tracks_use_case(playlist_id, track_order)

            # Assert
            assert result["status"] == "error"
            assert "validation failed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_tracks_use_case_success(self, operations_service, mock_repository_adapter):
        """Test successful track deletion."""
        # Arrange
        playlist_id = "test-playlist"
        track_numbers = [1, 3]
        mock_playlist_data = {
            "tracks": [
                {"track_number": 1, "title": "Track 1"},
                {"track_number": 2, "title": "Track 2"},
                {"track_number": 3, "title": "Track 3"},
            ]
        }
        mock_repository_adapter.get_playlist_by_id.return_value = mock_playlist_data
        mock_repository_adapter.replace_tracks.return_value = True

        # Act
        result = await operations_service.delete_tracks_use_case(playlist_id, track_numbers)

        # Assert
        assert result["status"] == "success"
        assert "2 tracks" in result["message"]
        # Should only keep track 2
        call_args = mock_repository_adapter.replace_tracks.call_args
        remaining_tracks = call_args[0][1]
        assert len(remaining_tracks) == 1
        assert remaining_tracks[0]["track_number"] == 2

    @pytest.mark.asyncio
    async def test_delete_tracks_playlist_not_found(self, operations_service, mock_repository_adapter):
        """Test track deletion when playlist not found."""
        # Arrange
        playlist_id = "non-existent"
        track_numbers = [1, 3]
        mock_repository_adapter.get_playlist_by_id.return_value = None

        # Act
        result = await operations_service.delete_tracks_use_case(playlist_id, track_numbers)

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_update_playlist_use_case_success(self, operations_service, mock_repository_adapter):
        """Test successful playlist update."""
        # Arrange
        playlist_id = "test-playlist"
        updates = {"title": "Updated Title", "description": "Updated description"}
        mock_repository_adapter.update_playlist.return_value = True

        # Act
        result = await operations_service.update_playlist_use_case(playlist_id, updates)

        # Assert
        assert result is True
        mock_repository_adapter.update_playlist.assert_called_once_with(playlist_id, updates)

    @pytest.mark.asyncio
    async def test_update_playlist_use_case_failure(self, operations_service, mock_repository_adapter):
        """Test playlist update failure."""
        # Arrange
        playlist_id = "test-playlist"
        updates = {"title": "Updated Title"}
        mock_repository_adapter.update_playlist.return_value = False

        # Act
        result = await operations_service.update_playlist_use_case(playlist_id, updates)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_playlist_use_case_success(self, operations_service, mock_repository_adapter):
        """Test successful playlist deletion."""
        # Arrange
        playlist_id = "test-playlist"
        mock_repository_adapter.delete_playlist.return_value = True

        # Act
        result = await operations_service.delete_playlist_use_case(playlist_id)

        # Assert
        assert result is True
        mock_repository_adapter.delete_playlist.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_associate_nfc_tag_use_case_success(self, operations_service, mock_repository_adapter):
        """Test successful NFC tag association."""
        # Arrange
        playlist_id = "test-playlist"
        nfc_tag_id = "nfc-123"
        mock_repository_adapter.update_playlist.return_value = True

        # Act
        result = await operations_service.associate_nfc_tag_use_case(playlist_id, nfc_tag_id)

        # Assert
        assert result is True
        mock_repository_adapter.update_playlist.assert_called_once_with(
            playlist_id, {"nfc_tag_id": nfc_tag_id}
        )

    @pytest.mark.asyncio
    async def test_disassociate_nfc_tag_use_case_success(self, operations_service, mock_repository_adapter):
        """Test successful NFC tag disassociation."""
        # Arrange
        playlist_id = "test-playlist"
        mock_repository_adapter.update_playlist.return_value = True

        # Act
        result = await operations_service.disassociate_nfc_tag_use_case(playlist_id)

        # Assert
        assert result is True
        mock_repository_adapter.update_playlist.assert_called_once_with(
            playlist_id, {"nfc_tag_id": None}
        )

    @pytest.mark.asyncio
    async def test_find_playlist_by_nfc_tag_use_case_found(self, operations_service, mock_playlist_app_service):
        """Test finding playlist by NFC tag when playlist exists."""
        # Arrange
        nfc_tag_id = "nfc-123"
        mock_playlists = [
            {"id": "1", "title": "Playlist 1", "nfc_tag_id": None},
            {"id": "2", "title": "Playlist 2", "nfc_tag_id": nfc_tag_id},
            {"id": "3", "title": "Playlist 3", "nfc_tag_id": "other-nfc"},
        ]
        mock_playlist_app_service.get_playlists_use_case.return_value = {
            "status": "success",
            "playlists": mock_playlists
        }

        # Act
        result = await operations_service.find_playlist_by_nfc_tag_use_case(nfc_tag_id)

        # Assert
        assert result is not None
        assert result["id"] == "2"
        assert result["nfc_tag_id"] == nfc_tag_id

    @pytest.mark.asyncio
    async def test_find_playlist_by_nfc_tag_use_case_not_found(self, operations_service, mock_playlist_app_service):
        """Test finding playlist by NFC tag when playlist doesn't exist."""
        # Arrange
        nfc_tag_id = "non-existent-nfc"
        mock_playlists = [
            {"id": "1", "title": "Playlist 1", "nfc_tag_id": None},
            {"id": "2", "title": "Playlist 2", "nfc_tag_id": "other-nfc"},
        ]
        mock_playlist_app_service.get_playlists_use_case.return_value = {
            "status": "success",
            "playlists": mock_playlists
        }

        # Act
        result = await operations_service.find_playlist_by_nfc_tag_use_case(nfc_tag_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_sync_playlists_use_case_success(self, operations_service, mock_playlist_app_service):
        """Test successful playlist synchronization."""
        # Arrange
        mock_playlists = [
            {"id": "1", "title": "Playlist 1"},
            {"id": "2", "title": "Playlist 2"},
        ]
        mock_playlist_app_service.get_playlists_use_case.return_value = {
            "status": "success",
            "playlists": mock_playlists
        }

        # Act
        result = await operations_service.sync_playlists_use_case()

        # Assert
        assert result["status"] == "success"
        assert result["playlists"] == mock_playlists
        assert "synchronized" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_move_track_between_playlists_use_case(self, operations_service):
        """Test track movement between playlists (placeholder implementation)."""
        # Arrange
        source_playlist_id = "source-playlist"
        target_playlist_id = "target-playlist"
        track_number = 2
        target_position = 1

        # Act
        result = await operations_service.move_track_between_playlists_use_case(
            source_playlist_id, target_playlist_id, track_number, target_position
        )

        # Assert
        assert result["status"] == "success"
        assert "not yet implemented" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_validate_playlist_integrity_valid(self, operations_service, mock_playlist_app_service):
        """Test playlist integrity validation for valid playlist."""
        # Arrange
        playlist_id = "test-playlist"
        mock_playlist_data = {
            "id": playlist_id,
            "tracks": [
                {"track_number": 1, "title": "Track 1"},
                {"track_number": 2, "title": "Track 2"},
                {"track_number": 3, "title": "Track 3"},
            ]
        }
        mock_playlist_app_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": mock_playlist_data
        }

        # Act
        result = await operations_service.validate_playlist_integrity(playlist_id)

        # Assert
        assert result["status"] == "success"
        assert result["valid"] is True
        assert result["track_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_playlist_integrity_invalid_numbering(self, operations_service, mock_playlist_app_service):
        """Test playlist integrity validation for invalid track numbering."""
        # Arrange
        playlist_id = "test-playlist"
        mock_playlist_data = {
            "id": playlist_id,
            "tracks": [
                {"track_number": 1, "title": "Track 1"},
                {"track_number": 3, "title": "Track 3"},  # Missing track 2
                {"track_number": 5, "title": "Track 5"},  # Wrong number
            ]
        }
        mock_playlist_app_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": mock_playlist_data
        }

        # Act
        result = await operations_service.validate_playlist_integrity(playlist_id)

        # Assert
        assert result["status"] == "warning"
        assert result["valid"] is False
        assert "inconsistency" in result["message"].lower()
        assert "details" in result

    @pytest.mark.asyncio
    async def test_validate_playlist_integrity_not_found(self, operations_service, mock_playlist_app_service):
        """Test playlist integrity validation when playlist not found."""
        # Arrange
        playlist_id = "non-existent"
        mock_playlist_app_service.get_playlist_use_case.return_value = {
            "status": "error",
            "playlist": None
        }

        # Act
        result = await operations_service.validate_playlist_integrity(playlist_id)

        # Assert
        assert result["status"] == "error"
        assert result["valid"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_error_handling(self, operations_service, mock_repository_adapter):
        """Test error handling in service methods."""
        # Arrange
        mock_repository_adapter.get_playlist_by_id.side_effect = Exception("Database error")

        # Act
        result = await operations_service.reorder_tracks_use_case("test-id", [1, 2, 3])

        # Assert
        assert result["status"] == "error"
        assert "database error" in result["message"].lower()

    def test_single_responsibility_principle(self, operations_service):
        """Test that the service follows Single Responsibility Principle."""
        # The service should only handle complex operations orchestration
        assert hasattr(operations_service, '_playlist_app_service')
        assert hasattr(operations_service, '_repository_adapter')

        # Should not have HTTP handling methods
        assert not hasattr(operations_service, 'handle_request')
        assert not hasattr(operations_service, 'create_response')

        # Should not have broadcasting methods
        assert not hasattr(operations_service, 'broadcast_state')

        # Should have orchestration methods
        orchestration_methods = [
            'reorder_tracks_use_case',
            'delete_tracks_use_case',
            'update_playlist_use_case',
            'delete_playlist_use_case',
            'associate_nfc_tag_use_case',
            'disassociate_nfc_tag_use_case',
            'find_playlist_by_nfc_tag_use_case',
            'sync_playlists_use_case',
            'move_track_between_playlists_use_case',
            'validate_playlist_integrity'
        ]

        for method in orchestration_methods:
            assert hasattr(operations_service, method)

    def test_service_initialization(self, mock_playlist_app_service):
        """Test service initialization."""
        # Act
        service = PlaylistOperationsService(mock_playlist_app_service)

        # Assert
        assert service._playlist_app_service == mock_playlist_app_service
        assert service._repository_adapter is not None  # Should use default

    def test_service_initialization_with_repository(self, mock_playlist_app_service, mock_repository_adapter):
        """Test service initialization with custom repository."""
        # Act
        service = PlaylistOperationsService(mock_playlist_app_service, mock_repository_adapter)

        # Assert
        assert service._playlist_app_service == mock_playlist_app_service
        assert service._repository_adapter == mock_repository_adapter