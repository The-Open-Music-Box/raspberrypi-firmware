# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Broadcasting Contract Validation Tests

Tests the runtime validation in UnifiedBroadcastingService that prevents
contract violations like issue #71 from reaching the frontend.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.services.broadcasting.unified_broadcasting_service import UnifiedBroadcastingService


class TestBroadcastingContractValidation:
    """Test runtime contract validation in broadcasting service."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager for testing."""
        manager = Mock()
        manager.broadcast_state_change = AsyncMock()
        manager.send_acknowledgment = AsyncMock()
        return manager

    @pytest.fixture
    def broadcasting_service(self, mock_state_manager):
        """Create broadcasting service instance."""
        return UnifiedBroadcastingService(mock_state_manager)

    def test_validate_and_fix_contract_adds_missing_number_field(self, broadcasting_service):
        """Test that validation auto-fixes missing 'number' field."""
        # Simulate buggy serialization output (like the bug in issue #71)
        buggy_playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {
                    'id': 'track-1',
                    'number': 1,  # Has this
                    # 'number': 1,  # MISSING - the bug!
                    'title': 'Test Track',
                    'filename': 'test.mp3',
                    'duration_ms': 180000
                }
            ]
        }

        # Validate and fix
        fixed_playlist = broadcasting_service._validate_and_fix_contract(buggy_playlist)

        # Verify fix
        assert 'number' in fixed_playlist['tracks'][0], \
            "Validation should add missing 'number' field"
        assert fixed_playlist['tracks'][0]['number'] == 1, \
            "Added 'number' should match 'number'"

    def test_validate_and_fix_contract_handles_multiple_tracks(self, broadcasting_service):
        """Test validation fixes multiple tracks."""
        playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {'id': 't1', 'number': 1, 'title': 'Track 1', 'filename': 't1.mp3', 'duration_ms': 1000},
                {'id': 't2', 'number': 2, 'title': 'Track 2', 'filename': 't2.mp3', 'duration_ms': 2000},
                {'id': 't3', 'number': 3, 'title': 'Track 3', 'filename': 't3.mp3', 'duration_ms': 3000},
            ]
        }

        fixed_playlist = broadcasting_service._validate_and_fix_contract(playlist)

        # All tracks should have 'number' field
        for idx, track in enumerate(fixed_playlist['tracks'], 1):
            assert 'number' in track, f"Track {idx} missing 'number' field"
            assert track['number'] == idx, f"Track {idx} has wrong 'number' value"

    def test_validate_and_fix_contract_preserves_correct_tracks(self, broadcasting_service):
        """Test that validation doesn't break correctly serialized tracks."""
        correct_playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {
                    'id': 'track-1',
                    'number': 1,
                    'number': 1,  # Already present
                    'title': 'Test Track',
                    'filename': 'test.mp3',
                    'duration_ms': 180000
                }
            ]
        }

        fixed_playlist = broadcasting_service._validate_and_fix_contract(correct_playlist)

        # Should remain unchanged
        assert fixed_playlist['tracks'][0]['number'] == 1
        assert fixed_playlist['tracks'][0]['number'] == 1

    def test_validate_and_fix_contract_fixes_field_mismatch(self, broadcasting_service):
        """Test validation fixes mismatched number/track_number fields."""
        mismatched_playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {
                    'id': 'track-1',
                    'number': 5,
                    'number': 3,  # WRONG - doesn't match track_number
                    'title': 'Test Track',
                    'filename': 'test.mp3',
                    'duration_ms': 180000
                }
            ]
        }

        fixed_playlist = broadcasting_service._validate_and_fix_contract(mismatched_playlist)

        # Should use track_number as source of truth
        assert fixed_playlist['tracks'][0]['number'] == 5, \
            "Should fix 'number' to match 'number'"

    def test_validate_and_fix_contract_handles_empty_playlist(self, broadcasting_service):
        """Test validation handles playlist with no tracks."""
        empty_playlist = {
            'id': 'empty-playlist',
            'title': 'Empty Playlist',
            'tracks': []
        }

        fixed_playlist = broadcasting_service._validate_and_fix_contract(empty_playlist)

        # Should handle gracefully
        assert fixed_playlist['tracks'] == []

    def test_validate_and_fix_contract_handles_missing_tracks_field(self, broadcasting_service):
        """Test validation handles playlist without tracks field."""
        no_tracks_playlist = {
            'id': 'no-tracks',
            'title': 'No Tracks'
            # No 'tracks' field
        }

        fixed_playlist = broadcasting_service._validate_and_fix_contract(no_tracks_playlist)

        # Should return unchanged
        assert 'tracks' not in fixed_playlist

    def test_validate_and_fix_contract_handles_invalid_input(self, broadcasting_service):
        """Test validation handles invalid input gracefully."""
        # Test with None
        result = broadcasting_service._validate_and_fix_contract(None)
        assert result is None

        # Test with non-dict
        result = broadcasting_service._validate_and_fix_contract("not a dict")
        assert result == "not a dict"

    def test_validate_and_fix_contract_doesnt_mutate_original(self, broadcasting_service):
        """Test that validation doesn't mutate the original data."""
        original = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {'id': 't1', 'number': 1, 'title': 'Track 1', 'filename': 't1.mp3', 'duration_ms': 1000}
            ]
        }

        original_tracks_ref = original['tracks']
        original_track_count = len(original['tracks'])

        fixed_playlist = broadcasting_service._validate_and_fix_contract(original)

        # Original should not be mutated
        assert original['tracks'] is original_tracks_ref, \
            "Original tracks list should not be replaced"
        assert len(original['tracks']) == original_track_count, \
            "Original tracks count should not change"

    @pytest.mark.asyncio
    async def test_broadcast_playlist_change_validates_contract(
        self, broadcasting_service, mock_state_manager
    ):
        """Test that broadcast_playlist_change validates data before broadcasting."""
        buggy_playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {
                    'id': 'track-1',
                    'number': 1,
                    # Missing 'number' field
                    'title': 'Test Track',
                    'filename': 'test.mp3',
                    'duration_ms': 180000
                }
            ]
        }

        # Broadcast (should auto-fix)
        await broadcasting_service.broadcast_playlist_change(
            playlist_id='test-playlist',
            change_type='updated',
            playlist_data=buggy_playlist
        )

        # Verify broadcast was called
        assert mock_state_manager.broadcast_state_change.called

        # Get the actual data that was broadcast
        broadcast_call = mock_state_manager.broadcast_state_change.call_args
        broadcast_data = broadcast_call[0][1]  # Second argument is data

        # Verify the broadcast included fixed data
        if 'playlist' in broadcast_data:
            playlist = broadcast_data['playlist']
            if 'tracks' in playlist and len(playlist['tracks']) > 0:
                assert 'number' in playlist['tracks'][0], \
                    "Broadcast should include fixed 'number' field"


class TestContractValidationLogging:
    """Test that contract validation logs appropriate warnings."""

    @pytest.fixture
    def broadcasting_service(self):
        """Create broadcasting service for logging tests."""
        mock_manager = Mock()
        mock_manager.broadcast_state_change = AsyncMock()
        return UnifiedBroadcastingService(mock_manager)

    def test_validation_logs_warning_for_missing_number(self, broadcasting_service, caplog):
        """Test that validation logs warning when fixing missing 'number' field."""
        import logging
        caplog.set_level(logging.WARNING)

        buggy_playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {'id': 't1', 'number': 1, 'title': 'Track', 'filename': 'track.mp3', 'duration_ms': 1000}
            ]
        }

        broadcasting_service._validate_and_fix_contract(buggy_playlist)

        # Check that warning was logged
        assert any('CONTRACT VIOLATION FIXED' in record.message for record in caplog.records), \
            "Should log warning about missing 'number' field"

    def test_validation_logs_error_for_unfixable_track(self, broadcasting_service, caplog):
        """Test that validation logs error for tracks that can't be fixed."""
        import logging
        caplog.set_level(logging.ERROR)

        unfixable_playlist = {
            'id': 'test-playlist',
            'title': 'Test Playlist',
            'tracks': [
                {
                    'id': 't1',
                    # Missing both 'number' AND 'number'
                    'title': 'Broken Track',
                    'filename': 'broken.mp3',
                    'duration_ms': 1000
                }
            ]
        }

        broadcasting_service._validate_and_fix_contract(unfixable_playlist)

        # Check that error was logged
        assert any('CONTRACT VIOLATION CANNOT FIX' in record.message for record in caplog.records), \
            "Should log error for unfixable tracks"
