"""
Comprehensive tests for Playlist domain entity.

Tests cover:
- Factory methods
- Domain behaviors (add, remove, reorder)
- Domain queries (get, has, is_valid, etc.)
- Business rules and invariants
- Edge cases and error handling
"""

import pytest
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track


class TestPlaylistConstruction:
    """Test playlist construction and initialization."""

    def test_create_playlist_minimal(self):
        """Test creating playlist with minimal required fields."""
        playlist = Playlist(title="Test Playlist")

        assert playlist.title == "Test Playlist"
        assert playlist.tracks == []
        assert playlist.description is None
        assert playlist.id is None
        assert playlist.nfc_tag_id is None

    def test_create_playlist_full(self):
        """Test creating playlist with all fields."""
        tracks = [Track.from_file("/path/to/song.mp3", 1)]
        playlist = Playlist(
            title="Full Playlist",
            tracks=tracks,
            description="A complete playlist",
            id="playlist-123",
            nfc_tag_id="tag-456",
            path="/playlists/full"
        )

        assert playlist.title == "Full Playlist"
        assert len(playlist.tracks) == 1
        assert playlist.description == "A complete playlist"
        assert playlist.id == "playlist-123"
        assert playlist.nfc_tag_id == "tag-456"
        assert playlist.path == "/playlists/full"

    def test_title_property_alias(self):
        """Test title property is aliased to name."""
        playlist = Playlist(title="Test")

        assert playlist.title == "Test"
        assert playlist.title == playlist.title

    def test_title_setter(self):
        """Test title setter updates name."""
        playlist = Playlist(title="Original")
        playlist.title = "Updated"

        assert playlist.title == "Updated"
        assert playlist.title == "Updated"


class TestPlaylistFactoryMethods:
    """Test playlist factory methods."""

    def test_from_api_data_with_title(self):
        """Test creating playlist from API data using title parameter."""
        playlist = Playlist.from_api_data(title="API Playlist", description="From API")

        assert playlist.title == "API Playlist"
        assert playlist.description == "From API"

    def test_from_api_data_with_name(self):
        """Test creating playlist from API data using name parameter."""
        playlist = Playlist.from_api_data(name="Named Playlist")

        assert playlist.title == "Named Playlist"

    def test_from_api_data_title_precedence(self):
        """Test title takes precedence over name when both provided."""
        playlist = Playlist.from_api_data(title="Title", name="Name")

        assert playlist.title == "Title"

    def test_from_api_data_no_name_raises_error(self):
        """Test creating playlist without title or name raises ValueError."""
        with pytest.raises(ValueError, match="Either title or name must be provided"):
            Playlist.from_api_data()

    def test_from_files_creates_tracks(self):
        """Test creating playlist from file paths creates tracks."""
        file_paths = ["/music/song1.mp3", "/music/song2.mp3", "/music/song3.mp3"]
        playlist = Playlist.from_files("File Playlist", file_paths)

        assert playlist.title == "File Playlist"
        assert len(playlist.tracks) == 3
        assert playlist.tracks[0].track_number == 1
        assert playlist.tracks[1].track_number == 2
        assert playlist.tracks[2].track_number == 3
        assert playlist.tracks[0].filename == "song1.mp3"

    def test_from_files_empty_list(self):
        """Test creating playlist from empty file list."""
        playlist = Playlist.from_files("Empty", [])

        assert playlist.title == "Empty"
        assert playlist.tracks == []


class TestPlaylistTrackOperations:
    """Test track manipulation operations."""

    def test_add_track_with_number(self):
        """Test adding track with explicit track number."""
        playlist = Playlist(title="Test")
        track = Track.from_file("/music/song.mp3", 5)

        playlist.add_track(track)

        assert len(playlist.tracks) == 1
        assert playlist.tracks[0].track_number == 5

    def test_add_track_auto_number(self):
        """Test adding track with auto-assigned number."""
        playlist = Playlist(title="Test")
        track1 = Track.from_file("/music/song1.mp3", 1)
        track2 = Track.from_file("/music/song2.mp3", 0)  # Will be auto-numbered

        playlist.add_track(track1)
        playlist.add_track(track2)

        assert track2.track_number == 2

    def test_add_track_maintains_sort_order(self):
        """Test adding tracks maintains sorted order."""
        playlist = Playlist(title="Test")
        track3 = Track.from_file("/music/song3.mp3", 3)
        track1 = Track.from_file("/music/song1.mp3", 1)
        track2 = Track.from_file("/music/song2.mp3", 2)

        playlist.add_track(track3)
        playlist.add_track(track1)
        playlist.add_track(track2)

        assert playlist.tracks[0].track_number == 1
        assert playlist.tracks[1].track_number == 2
        assert playlist.tracks[2].track_number == 3

    def test_get_track_exists(self):
        """Test getting track by number when it exists."""
        playlist = Playlist.from_files("Test", ["/song1.mp3", "/song2.mp3"])

        track = playlist.get_track(2)

        assert track is not None
        assert track.track_number == 2

    def test_get_track_not_exists(self):
        """Test getting track by number when it doesn't exist."""
        playlist = Playlist.from_files("Test", ["/song1.mp3"])

        track = playlist.get_track(99)

        assert track is None

    def test_remove_track_exists(self):
        """Test removing track that exists."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3", "/s3.mp3"])

        removed = playlist.remove_track(2)

        assert removed is not None
        assert removed.track_number == 2
        assert len(playlist.tracks) == 2

    def test_remove_track_reindexes(self):
        """Test removing track reindexes remaining tracks."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3", "/s3.mp3"])

        playlist.remove_track(2)

        # Tracks should be reindexed to 1, 2
        assert playlist.tracks[0].track_number == 1
        assert playlist.tracks[1].track_number == 2

    def test_remove_track_not_exists(self):
        """Test removing track that doesn't exist."""
        playlist = Playlist.from_files("Test", ["/song.mp3"])

        removed = playlist.remove_track(99)

        assert removed is None
        assert len(playlist.tracks) == 1


class TestPlaylistQueries:
    """Test playlist query methods."""

    def test_get_first_track_with_tracks(self):
        """Test getting first track from non-empty playlist."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3"])

        first = playlist.get_first_track()

        assert first is not None
        assert first.track_number == 1

    def test_get_first_track_empty_playlist(self):
        """Test getting first track from empty playlist."""
        playlist = Playlist(title="Empty")

        first = playlist.get_first_track()

        assert first is None

    def test_get_first_track_non_sequential_numbers(self):
        """Test getting first track with non-sequential numbering."""
        playlist = Playlist(title="Test")
        track5 = Track.from_file("/s5.mp3", 5)
        track3 = Track.from_file("/s3.mp3", 3)
        playlist.tracks = [track5, track3]

        first = playlist.get_first_track()

        assert first.track_number == 3

    def test_get_track_by_position_valid(self):
        """Test getting track by position."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3", "/s3.mp3"])

        track = playlist.get_track_by_position(1)

        assert track is not None
        assert track.track_number == 2

    def test_get_track_by_position_negative(self):
        """Test getting track by negative position."""
        playlist = Playlist.from_files("Test", ["/song.mp3"])

        track = playlist.get_track_by_position(-1)

        assert track is None

    def test_get_track_by_position_out_of_bounds(self):
        """Test getting track by position out of bounds."""
        playlist = Playlist.from_files("Test", ["/song.mp3"])

        track = playlist.get_track_by_position(10)

        assert track is None

    def test_get_track_numbers(self):
        """Test getting all track numbers sorted."""
        playlist = Playlist(title="Test")
        playlist.tracks = [
            Track.from_file("/s3.mp3", 3),
            Track.from_file("/s1.mp3", 1),
            Track.from_file("/s5.mp3", 5)
        ]

        numbers = playlist.get_track_numbers()

        assert numbers == [1, 3, 5]

    def test_has_track_number_exists(self):
        """Test checking if track number exists."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3"])

        assert playlist.has_track_number(1) is True
        assert playlist.has_track_number(2) is True

    def test_has_track_number_not_exists(self):
        """Test checking if track number doesn't exist."""
        playlist = Playlist.from_files("Test", ["/s1.mp3"])

        assert playlist.has_track_number(99) is False

    def test_get_min_track_number(self):
        """Test getting minimum track number."""
        playlist = Playlist(title="Test")
        playlist.tracks = [
            Track.from_file("/s5.mp3", 5),
            Track.from_file("/s2.mp3", 2),
            Track.from_file("/s8.mp3", 8)
        ]

        assert playlist.get_min_track_number() == 2

    def test_get_min_track_number_empty(self):
        """Test getting minimum track number from empty playlist."""
        playlist = Playlist(title="Empty")

        assert playlist.get_min_track_number() is None

    def test_get_max_track_number(self):
        """Test getting maximum track number."""
        playlist = Playlist(title="Test")
        playlist.tracks = [
            Track.from_file("/s5.mp3", 5),
            Track.from_file("/s2.mp3", 2),
            Track.from_file("/s8.mp3", 8)
        ]

        assert playlist.get_max_track_number() == 8

    def test_get_max_track_number_empty(self):
        """Test getting maximum track number from empty playlist."""
        playlist = Playlist(title="Empty")

        assert playlist.get_max_track_number() is None

    def test_is_empty_true(self):
        """Test checking if playlist is empty."""
        playlist = Playlist(title="Empty")

        assert playlist.is_empty() is True

    def test_is_empty_false(self):
        """Test checking if playlist is not empty."""
        playlist = Playlist.from_files("Test", ["/song.mp3"])

        assert playlist.is_empty() is False

    def test_len_operator(self):
        """Test len() operator on playlist."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3", "/s3.mp3"])

        assert len(playlist) == 3


class TestPlaylistBusinessRules:
    """Test playlist business rules and validation."""

    def test_normalize_track_numbers_sequential(self):
        """Test normalizing track numbers."""
        playlist = Playlist(title="Test")
        track5 = Track.from_file("/s5.mp3", 5)
        track10 = Track.from_file("/s10.mp3", 10)
        track20 = Track.from_file("/s20.mp3", 20)
        playlist.tracks = [track10, track5, track20]

        playlist.normalize_track_numbers()

        # After normalization, track 5 becomes 1, track 10 becomes 2, track 20 becomes 3
        assert track5.track_number == 1
        assert track10.track_number == 2
        assert track20.track_number == 3

    def test_normalize_track_numbers_preserves_order(self):
        """Test normalization preserves original order."""
        playlist = Playlist(title="Test")
        track5 = Track.from_file("/five.mp3", 5)
        track20 = Track.from_file("/twenty.mp3", 20)
        track10 = Track.from_file("/ten.mp3", 10)
        playlist.tracks = [track5, track20, track10]

        playlist.normalize_track_numbers()

        # Order should be 5 -> 1, 10 -> 2, 20 -> 3
        assert track5.track_number == 1
        assert track10.track_number == 2
        assert track20.track_number == 3

    def test_normalize_track_numbers_empty_playlist(self):
        """Test normalizing empty playlist doesn't crash."""
        playlist = Playlist(title="Empty")

        playlist.normalize_track_numbers()  # Should not raise

        assert len(playlist.tracks) == 0

    def test_is_valid_true(self):
        """Test playlist is valid."""
        playlist = Playlist.from_files("Valid Playlist", ["/song.mp3"])

        assert playlist.is_valid() is True

    def test_is_valid_empty_name(self):
        """Test playlist with empty name is invalid."""
        playlist = Playlist(title="  ")
        playlist.tracks = [Track.from_file("/song.mp3", 1)]

        assert playlist.is_valid() is False

    def test_is_valid_invalid_track(self):
        """Test playlist with invalid track is invalid."""
        playlist = Playlist(title="Test")
        invalid_track = Track(
            track_number=0,  # Invalid: must be > 0
            title="",
            filename="",
            file_path=""
        )
        playlist.tracks = [invalid_track]

        assert playlist.is_valid() is False

    def test_is_valid_empty_playlist(self):
        """Test empty playlist with valid name is still valid."""
        playlist = Playlist(title="Empty but Valid")

        assert playlist.is_valid() is True


class TestPlaylistCalculations:
    """Test playlist calculation methods."""

    def test_get_total_duration_all_tracks_have_duration(self):
        """Test total duration when all tracks have duration."""
        playlist = Playlist(title="Test")
        track1 = Track.from_file("/s1.mp3", 1)
        track1.duration_ms = 180000  # 3 minutes
        track2 = Track.from_file("/s2.mp3", 2)
        track2.duration_ms = 240000  # 4 minutes
        playlist.tracks = [track1, track2]

        total = playlist.get_total_duration_ms()

        assert total == 420000  # 7 minutes

    def test_get_total_duration_some_tracks_missing_duration(self):
        """Test total duration when some tracks missing duration."""
        playlist = Playlist(title="Test")
        track1 = Track.from_file("/s1.mp3", 1)
        track1.duration_ms = 180000
        track2 = Track.from_file("/s2.mp3", 2)
        track2.duration_ms = None
        playlist.tracks = [track1, track2]

        total = playlist.get_total_duration_ms()

        assert total is None

    def test_get_total_duration_empty_playlist(self):
        """Test total duration of empty playlist."""
        playlist = Playlist(title="Empty")

        total = playlist.get_total_duration_ms()

        # Empty playlist has no tracks with unknown duration, so returns 0
        assert total == 0

    def test_get_display_name_with_tracks(self):
        """Test display name with tracks."""
        playlist = Playlist.from_files("My Playlist", ["/s1.mp3", "/s2.mp3", "/s3.mp3"])

        display_name = playlist.get_display_name()

        assert display_name == "My Playlist (3 tracks)"

    def test_get_display_name_empty(self):
        """Test display name for empty playlist."""
        playlist = Playlist(title="Empty Playlist")

        display_name = playlist.get_display_name()

        assert display_name == "Empty Playlist (empty)"

    def test_get_display_name_single_track(self):
        """Test display name with single track."""
        playlist = Playlist.from_files("Single", ["/song.mp3"])

        display_name = playlist.get_display_name()

        assert display_name == "Single (1 tracks)"


class TestPlaylistEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_add_same_track_multiple_times(self):
        """Test adding same track multiple times."""
        playlist = Playlist(title="Test")
        track = Track.from_file("/song.mp3", 1)

        playlist.add_track(track)
        playlist.add_track(track)

        # Should allow duplicates (business decision)
        assert len(playlist.tracks) == 2

    def test_track_numbers_with_gaps(self):
        """Test playlist handles track numbers with gaps."""
        playlist = Playlist(title="Test")
        playlist.tracks = [
            Track.from_file("/s1.mp3", 1),
            Track.from_file("/s10.mp3", 10),
            Track.from_file("/s100.mp3", 100)
        ]

        numbers = playlist.get_track_numbers()

        assert numbers == [1, 10, 100]
        assert playlist.get_first_track().track_number == 1

    def test_special_characters_in_name(self):
        """Test playlist name with special characters."""
        playlist = Playlist(title="Test's 'Awesome' Playlist! 🎵")

        assert playlist.title == "Test's 'Awesome' Playlist! 🎵"
        assert playlist.is_valid() is True

    def test_very_long_playlist(self):
        """Test playlist with many tracks."""
        file_paths = [f"/song{i}.mp3" for i in range(1000)]
        playlist = Playlist.from_files("Large Playlist", file_paths)

        assert len(playlist.tracks) == 1000
        assert playlist.get_max_track_number() == 1000
        assert playlist.get_min_track_number() == 1
