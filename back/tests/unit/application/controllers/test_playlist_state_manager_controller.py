"""
Comprehensive tests for PlaylistStateManager controller.

Tests cover:
- Track and Playlist dataclass serialization
- Playlist management (set, clear)
- Track navigation (current, next, previous, goto)
- Repeat modes (none, one, all)
- Shuffle functionality
- State queries and status
"""

import pytest
from app.src.application.controllers.playlist_state_manager_controller import (
    PlaylistStateManager, Playlist, Track
)


class TestTrackDataclass:
    """Test Track dataclass functionality."""

    def test_create_track(self):
        """Test creating track with required fields."""
        track = Track(
            id="track-1",
            title="Test Song",
            filename="test.mp3"
        )

        assert track.id == "track-1"
        assert track.title == "Test Song"
        assert track.filename == "test.mp3"
        assert track.duration_ms is None
        assert track.file_path is None

    def test_create_track_with_optional_fields(self):
        """Test creating track with all fields."""
        track = Track(
            id="track-2",
            title="Test Song",
            filename="test.mp3",
            duration_ms=180000,
            file_path="/music/test.mp3"
        )

        assert track.duration_ms == 180000
        assert track.file_path == "/music/test.mp3"

    def test_track_to_dict(self):
        """Test track serialization to dict."""
        track = Track(
            id="track-1",
            title="Song",
            filename="song.mp3",
            duration_ms=200000,
            file_path="/music/song.mp3"
        )

        result = track.to_dict()

        assert result["id"] == "track-1"
        assert result["title"] == "Song"
        assert result["filename"] == "song.mp3"
        assert result["duration_ms"] == 200000
        assert result["file_path"] == "/music/song.mp3"


class TestPlaylistDataclass:
    """Test Playlist dataclass functionality."""

    def test_create_empty_playlist(self):
        """Test creating empty playlist."""
        playlist = Playlist(id="pl-1", title="Test Playlist")

        assert playlist.id == "pl-1"
        assert playlist.title == "Test Playlist"
        assert playlist.tracks == []

    def test_create_playlist_with_tracks(self):
        """Test creating playlist with tracks."""
        tracks = [
            Track(id="t1", title="Song 1", filename="s1.mp3"),
            Track(id="t2", title="Song 2", filename="s2.mp3")
        ]

        playlist = Playlist(id="pl-1", title="Test", tracks=tracks)

        assert len(playlist.tracks) == 2

    def test_playlist_to_dict(self):
        """Test playlist serialization to dict."""
        tracks = [
            Track(id="t1", title="Song 1", filename="s1.mp3"),
            Track(id="t2", title="Song 2", filename="s2.mp3")
        ]
        playlist = Playlist(id="pl-1", title="Test", tracks=tracks)

        result = playlist.to_dict()

        assert result["id"] == "pl-1"
        assert result["title"] == "Test"
        assert result["total_tracks"] == 2
        assert len(result["tracks"]) == 2


class TestPlaylistStateManagerInitialization:
    """Test PlaylistStateManager initialization."""

    def test_create_manager(self):
        """Test creating state manager."""
        manager = PlaylistStateManager()

        assert manager._current_playlist is None
        assert manager._current_track_index == 0
        assert manager._repeat_mode == "none"
        assert manager._shuffle_enabled is False
        assert manager._shuffle_order == []


class TestPlaylistManagement:
    """Test playlist management operations."""

    @pytest.fixture
    def manager(self):
        """Create manager for testing."""
        return PlaylistStateManager()

    @pytest.fixture
    def sample_playlist(self):
        """Create sample playlist."""
        return Playlist(
            id="pl-1",
            title="Test Playlist",
            tracks=[
                Track(id="t1", title="Song 1", filename="s1.mp3"),
                Track(id="t2", title="Song 2", filename="s2.mp3"),
                Track(id="t3", title="Song 3", filename="s3.mp3"),
            ]
        )

    def test_set_playlist(self, manager, sample_playlist):
        """Test setting current playlist."""
        success = manager.set_playlist(sample_playlist)

        assert success is True
        assert manager._current_playlist == sample_playlist
        assert manager._current_track_index == 0

    def test_set_playlist_with_start_index(self, manager, sample_playlist):
        """Test setting playlist with custom start index."""
        success = manager.set_playlist(sample_playlist, start_index=1)

        assert success is True
        assert manager._current_track_index == 1

    def test_set_empty_playlist_fails(self, manager):
        """Test setting empty playlist fails."""
        empty_playlist = Playlist(id="pl-1", title="Empty", tracks=[])

        success = manager.set_playlist(empty_playlist)

        assert success is False

    def test_set_playlist_clamps_invalid_index(self, manager, sample_playlist):
        """Test setting playlist clamps invalid start index."""
        success = manager.set_playlist(sample_playlist, start_index=10)

        assert success is True
        assert manager._current_track_index == 2  # Last track

    def test_clear_playlist(self, manager, sample_playlist):
        """Test clearing playlist."""
        manager.set_playlist(sample_playlist)
        manager.clear_playlist()

        assert manager._current_playlist is None
        assert manager._current_track_index == 0
        assert manager._shuffle_order == []


class TestTrackNavigation:
    """Test track navigation methods."""

    @pytest.fixture
    def manager(self):
        """Create manager with loaded playlist."""
        mgr = PlaylistStateManager()
        playlist = Playlist(
            id="pl-1",
            title="Test",
            tracks=[
                Track(id="t1", title="Song 1", filename="s1.mp3"),
                Track(id="t2", title="Song 2", filename="s2.mp3"),
                Track(id="t3", title="Song 3", filename="s3.mp3"),
            ]
        )
        mgr.set_playlist(playlist)
        return mgr

    def test_get_current_track(self, manager):
        """Test getting current track."""
        track = manager.get_current_track()

        assert track is not None
        assert track.id == "t1"

    def test_get_current_track_when_no_playlist(self):
        """Test getting current track when no playlist loaded."""
        manager = PlaylistStateManager()

        track = manager.get_current_track()

        assert track is None

    def test_move_to_next(self, manager):
        """Test moving to next track."""
        track = manager.move_to_next()

        assert track is not None
        assert track.id == "t2"
        assert manager._current_track_index == 1

    def test_move_to_next_at_end_returns_none(self, manager):
        """Test moving to next at end returns None."""
        manager._current_track_index = 2  # Last track

        track = manager.move_to_next()

        assert track is None

    def test_move_to_previous(self, manager):
        """Test moving to previous track."""
        manager._current_track_index = 1  # Start at second track

        track = manager.move_to_previous()

        assert track is not None
        assert track.id == "t1"
        assert manager._current_track_index == 0

    def test_move_to_previous_at_beginning_returns_none(self, manager):
        """Test moving to previous at beginning returns None."""
        track = manager.move_to_previous()

        assert track is None

    def test_move_to_track_by_index(self, manager):
        """Test moving to specific track by index."""
        track = manager.move_to_track(2)

        assert track is not None
        assert track.id == "t3"
        assert manager._current_track_index == 2

    def test_move_to_invalid_track_index(self, manager):
        """Test moving to invalid index returns None."""
        track = manager.move_to_track(10)

        assert track is None

    def test_move_to_negative_index(self, manager):
        """Test moving to negative index returns None."""
        track = manager.move_to_track(-1)

        assert track is None


class TestRepeatMode:
    """Test repeat mode functionality."""

    @pytest.fixture
    def manager(self):
        """Create manager with playlist."""
        mgr = PlaylistStateManager()
        playlist = Playlist(
            id="pl-1",
            title="Test",
            tracks=[
                Track(id="t1", title="Song 1", filename="s1.mp3"),
                Track(id="t2", title="Song 2", filename="s2.mp3"),
            ]
        )
        mgr.set_playlist(playlist)
        return mgr

    def test_repeat_mode_none_stops_at_end(self, manager):
        """Test repeat none stops at end."""
        manager.set_repeat_mode("none")
        manager._current_track_index = 1

        track = manager.move_to_next()

        assert track is None

    def test_repeat_mode_all_loops_to_beginning(self, manager):
        """Test repeat all loops to beginning."""
        manager.set_repeat_mode("all")
        manager._current_track_index = 1

        track = manager.move_to_next()

        assert track is not None
        assert track.id == "t1"
        assert manager._current_track_index == 0

    def test_repeat_mode_one_stays_on_track(self, manager):
        """Test repeat one stays on current track."""
        manager.set_repeat_mode("one")

        track = manager.move_to_next()

        assert track is not None
        assert track.id == "t1"  # Same track

    def test_set_invalid_repeat_mode_ignored(self, manager):
        """Test setting invalid repeat mode is ignored."""
        manager.set_repeat_mode("invalid")

        assert manager._repeat_mode == "none"  # Unchanged


class TestShuffleMode:
    """Test shuffle functionality."""

    @pytest.fixture
    def manager(self):
        """Create manager with playlist."""
        mgr = PlaylistStateManager()
        playlist = Playlist(
            id="pl-1",
            title="Test",
            tracks=[
                Track(id=f"t{i}", title=f"Song {i}", filename=f"s{i}.mp3")
                for i in range(1, 11)  # 10 tracks
            ]
        )
        mgr.set_playlist(playlist)
        return mgr

    def test_set_shuffle_enabled(self, manager):
        """Test enabling shuffle."""
        manager.set_shuffle(True)

        assert manager._shuffle_enabled is True
        assert len(manager._shuffle_order) == 10
        assert manager._shuffle_order[0] == 0  # Current track first

    def test_set_shuffle_disabled(self, manager):
        """Test disabling shuffle."""
        manager.set_shuffle(True)
        manager.set_shuffle(False)

        assert manager._shuffle_enabled is False
        assert manager._shuffle_order == []

    def test_shuffle_order_includes_all_tracks(self, manager):
        """Test shuffle order includes all track indices."""
        manager.set_shuffle(True)

        assert sorted(manager._shuffle_order) == list(range(10))

    def test_next_track_with_shuffle(self, manager):
        """Test next track follows shuffle order."""
        manager.set_shuffle(True)

        # Move to next track
        track = manager.move_to_next()

        # Should get track at second position in shuffle order
        assert track.id == f"t{manager._shuffle_order[1] + 1}"

    def test_previous_track_with_shuffle(self, manager):
        """Test previous track follows shuffle order."""
        manager.set_shuffle(True)
        manager.move_to_next()  # Move to second position

        track = manager.move_to_previous()

        # Should get back to first track
        assert track.id == "t1"


class TestStateQueries:
    """Test state query methods."""

    @pytest.fixture
    def manager(self):
        """Create manager with playlist."""
        mgr = PlaylistStateManager()
        playlist = Playlist(
            id="pl-1",
            title="Test Playlist",
            tracks=[
                Track(id="t1", title="Song 1", filename="s1.mp3"),
                Track(id="t2", title="Song 2", filename="s2.mp3"),
                Track(id="t3", title="Song 3", filename="s3.mp3"),
            ]
        )
        mgr.set_playlist(playlist)
        return mgr

    def test_get_state(self, manager):
        """Test getting complete state."""
        state = manager.get_state()

        assert state["playlist"]["id"] == "pl-1"
        assert state["current_track"]["id"] == "t1"
        assert state["current_track_index"] == 0
        assert state["current_track_number"] == 1
        assert state["total_tracks"] == 3
        assert state["repeat_mode"] == "none"
        assert state["shuffle_enabled"] is False

    def test_can_go_next_true(self, manager):
        """Test can_go_next when possible."""
        assert manager.can_go_next() is True

    def test_can_go_next_false_at_end(self, manager):
        """Test can_go_next false at end without repeat."""
        manager._current_track_index = 2

        assert manager.can_go_next() is False

    def test_can_go_next_true_with_repeat_all(self, manager):
        """Test can_go_next true with repeat all."""
        manager.set_repeat_mode("all")
        manager._current_track_index = 2

        assert manager.can_go_next() is True

    def test_can_go_previous_false_at_beginning(self, manager):
        """Test can_go_previous false at beginning."""
        assert manager.can_go_previous() is False

    def test_can_go_previous_true_with_repeat_all(self, manager):
        """Test can_go_previous true with repeat all."""
        manager.set_repeat_mode("all")

        assert manager.can_go_previous() is True


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_navigation_on_empty_manager(self):
        """Test navigation methods on manager without playlist."""
        manager = PlaylistStateManager()

        assert manager.get_current_track() is None
        assert manager.move_to_next() is None
        assert manager.move_to_previous() is None
        assert manager.can_go_next() is False
        assert manager.can_go_previous() is False

    def test_shuffle_with_single_track(self):
        """Test shuffle with single track playlist."""
        manager = PlaylistStateManager()
        playlist = Playlist(
            id="pl-1",
            title="Single",
            tracks=[Track(id="t1", title="Song", filename="s.mp3")]
        )
        manager.set_playlist(playlist)
        manager.set_shuffle(True)

        assert len(manager._shuffle_order) == 1
        assert manager._shuffle_order[0] == 0
