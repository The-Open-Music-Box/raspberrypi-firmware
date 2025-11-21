"""
Verification tests for playlist broadcast synchronization fixes.

These tests verify that the critical broadcast fixes work correctly:
1. broadcast_playlist_updated sends full playlist data (not just updates)
2. broadcast_tracks_reordered sends full playlist via PLAYLISTS_SNAPSHOT
"""
import pytest
from unittest.mock import Mock, AsyncMock
from app.src.api.services.playlist_broadcasting_service import PlaylistBroadcastingService
from app.src.common.socket_events import StateEventType


@pytest.mark.asyncio
async def test_broadcast_playlist_updated_sends_full_playlist_data():
    """
    CRITICAL FIX VERIFICATION: Playlist updates must broadcast full playlist object.

    Before fix: Backend sent {playlist_id, updates: {title: "new"}}
    After fix: Backend sends {playlist_id, playlist: {...full data...}, updates}

    This ensures frontend handlePlaylistUpdated() receives data.playlist and works correctly.
    """
    # Mock state manager
    state_manager = Mock()
    state_manager.broadcast_state_change = AsyncMock()

    # Mock repository adapter that returns full playlist data
    repository_adapter = Mock()
    repository_adapter.get_playlist_by_id = AsyncMock(return_value={
        "id": "playlist-123",
        "title": "Updated Playlist Title",
        "description": "Updated Description",
        "track_count": 5,
        "nfc_tag_id": None,
        "tracks": [
            {"id": "track-1", "title": "Track 1", "track_number": 1, "filename": "track1.mp3"},
            {"id": "track-2", "title": "Track 2", "track_number": 2, "filename": "track2.mp3"},
        ]
    })

    # Create broadcasting service WITH repository
    broadcasting_service = PlaylistBroadcastingService(
        state_manager=state_manager,
        repository_adapter=repository_adapter
    )

    # Broadcast playlist update
    await broadcasting_service.broadcast_playlist_updated(
        playlist_id="playlist-123",
        updates={"title": "Updated Playlist Title"}
    )

    # Verify broadcast_state_change was called
    assert state_manager.broadcast_state_change.called

    # Get the call arguments
    call_args = state_manager.broadcast_state_change.call_args
    event_type = call_args[0][0]
    event_data = call_args[0][1]

    # Verify event type
    assert event_type == StateEventType.PLAYLIST_UPDATED

    # CRITICAL VERIFICATION: Event data must contain full playlist object
    assert "playlist" in event_data, "Missing 'playlist' key in event_data"
    assert event_data["playlist"] is not None, "Playlist data is None"

    # Verify full playlist structure
    playlist = event_data["playlist"]
    assert playlist["id"] == "playlist-123"
    assert playlist["title"] == "Updated Playlist Title"
    assert playlist["description"] == "Updated Description"
    assert playlist["track_count"] == 5
    assert "tracks" in playlist
    assert len(playlist["tracks"]) == 2

    # Verify backward compatibility - updates still included
    assert "updates" in event_data
    assert event_data["updates"]["title"] == "Updated Playlist Title"

    print("✅ Playlist update broadcasts full playlist data - Frontend will receive it correctly")


@pytest.mark.asyncio
async def test_broadcast_playlist_updated_fallback_without_repository():
    """Verify fallback behavior when repository is not available."""
    # Mock state manager
    state_manager = Mock()
    state_manager.broadcast_state_change = AsyncMock()

    # Create broadcasting service WITHOUT repository
    broadcasting_service = PlaylistBroadcastingService(
        state_manager=state_manager,
        repository_adapter=None
    )

    # Broadcast playlist update
    await broadcasting_service.broadcast_playlist_updated(
        playlist_id="playlist-456",
        updates={"title": "New Title"}
    )

    # Verify broadcast still happens (backward compatibility)
    assert state_manager.broadcast_state_change.called

    # Get the call arguments
    call_args = state_manager.broadcast_state_change.call_args
    event_data = call_args[0][1]

    # Without repository, should fall back to partial updates
    assert "updates" in event_data
    # May not have full playlist object, but still broadcasts

    print("✅ Fallback works when repository unavailable")


@pytest.mark.asyncio
async def test_broadcast_tracks_reordered_sends_via_playlists_snapshot():
    """
    CRITICAL FIX VERIFICATION: Track reordering must broadcast via PLAYLISTS_SNAPSHOT.

    Before fix: Backend sent state:tracks_reordered but frontend had no listener
    After fix: Backend sends state:playlists so existing frontend listener picks it up

    This ensures all clients see track reordering instantly.
    """
    # Mock state manager
    state_manager = Mock()
    state_manager.broadcast_state_change = AsyncMock()

    # Mock repository adapter with reordered tracks
    repository_adapter = Mock()
    repository_adapter.get_playlist_by_id = AsyncMock(return_value={
        "id": "playlist-789",
        "title": "Reordered Playlist",
        "track_count": 3,
        "tracks": [
            {"id": "track-3", "title": "Track 3", "track_number": 1, "filename": "track3.mp3"},
            {"id": "track-1", "title": "Track 1", "track_number": 2, "filename": "track1.mp3"},
            {"id": "track-2", "title": "Track 2", "track_number": 3, "filename": "track2.mp3"},
        ]
    })

    # Create broadcasting service WITH repository
    broadcasting_service = PlaylistBroadcastingService(
        state_manager=state_manager,
        repository_adapter=repository_adapter
    )

    # Broadcast tracks reordered
    await broadcasting_service.broadcast_tracks_reordered(
        playlist_id="playlist-789",
        track_order=[3, 1, 2]
    )

    # Verify broadcast_state_change was called
    assert state_manager.broadcast_state_change.called

    # Get the call arguments
    call_args = state_manager.broadcast_state_change.call_args
    event_type = call_args[0][0]
    event_data = call_args[0][1]

    # CRITICAL VERIFICATION: Must use PLAYLISTS_SNAPSHOT event type
    assert event_type == StateEventType.PLAYLISTS_SNAPSHOT, \
        f"Expected PLAYLISTS_SNAPSHOT for frontend compatibility, got {event_type}"

    # CRITICAL VERIFICATION: Event data must contain playlists array
    assert "playlists" in event_data, "Missing 'playlists' key"
    assert isinstance(event_data["playlists"], list), "playlists must be a list"
    assert len(event_data["playlists"]) == 1, "Should contain exactly one playlist"

    # Verify full playlist with reordered tracks
    playlist = event_data["playlists"][0]
    assert playlist["id"] == "playlist-789"
    assert "tracks" in playlist
    assert len(playlist["tracks"]) == 3

    # Verify track order is correct
    assert playlist["tracks"][0]["track_number"] == 1
    assert playlist["tracks"][0]["id"] == "track-3"
    assert playlist["tracks"][1]["track_number"] == 2
    assert playlist["tracks"][1]["id"] == "track-1"

    print("✅ Track reordering broadcasts via state:playlists - Frontend will receive it")


@pytest.mark.asyncio
async def test_broadcast_tracks_reordered_fallback_without_repository():
    """Verify fallback to old event type when repository unavailable."""
    # Mock state manager
    state_manager = Mock()
    state_manager.broadcast_state_change = AsyncMock()

    # Create broadcasting service WITHOUT repository
    broadcasting_service = PlaylistBroadcastingService(
        state_manager=state_manager,
        repository_adapter=None
    )

    # Broadcast tracks reordered
    await broadcasting_service.broadcast_tracks_reordered(
        playlist_id="playlist-999",
        track_order=[2, 1, 3]
    )

    # Verify broadcast still happens (backward compatibility)
    assert state_manager.broadcast_state_change.called

    # Get the call arguments
    call_args = state_manager.broadcast_state_change.call_args
    event_type = call_args[0][0]

    # Without repository, falls back to old TRACKS_REORDERED event
    assert event_type == StateEventType.TRACKS_REORDERED

    print("✅ Fallback to old event type when repository unavailable")
