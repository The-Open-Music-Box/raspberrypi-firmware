# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Comprehensive tests for domain models following Domain-Driven Design principles.

These tests verify that domain entities maintain their business logic integrity
and follow DDD patterns correctly.
"""

import pytest
from pathlib import Path

from app.src.domain.data.models.track import Track
from app.src.domain.data.models.playlist import Playlist


class TestTrackDomainEntity:
    """Test Track domain entity business logic."""
    
    def test_track_creation(self):
        """Test basic track creation."""
        track = Track(
            track_number=1,
            title="Test Song",
            filename="test.mp3",
            file_path="/music/test.mp3",
            duration_ms=180000,
            artist="Test Artist",
            album="Test Album"
        )
        
        assert track.track_number == 1
        assert track.title == "Test Song"
        assert track.filename == "test.mp3"
        assert track.file_path == "/music/test.mp3"
        assert track.duration_ms == 180000
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
    
    def test_track_domain_properties(self):
        """Test domain-specific properties."""
        track = Track(
            track_number=5,
            title="Test Track",
            filename="track.mp3",
            file_path="/music/track.mp3",
            duration_ms=240000
        )
        
        # Test API compatibility properties
        assert track.number == 5  # Alias for track_number
        assert track.path == Path("/music/track.mp3")  # Path conversion
        assert track.duration == 240.0  # Milliseconds to seconds
    
    def test_track_validation_business_rule(self):
        """Test domain business rule: track validation."""
        valid_track = Track(
            track_number=1,
            title="Valid Track",
            filename="valid.mp3",
            file_path="/music/valid.mp3"
        )
        
        assert valid_track.is_valid() is True
        
        # Invalid track: negative track number
        invalid_track = Track(
            track_number=-1,
            title="Invalid Track",
            filename="invalid.mp3",
            file_path="/music/invalid.mp3"
        )
        
        assert invalid_track.is_valid() is False
        
        # Invalid track: empty title
        invalid_track2 = Track(
            track_number=1,
            title="",
            filename="empty.mp3",
            file_path="/music/empty.mp3"
        )
        
        assert invalid_track2.is_valid() is False
    
    def test_track_display_name_domain_service(self):
        """Test domain service for display name formatting."""
        # Track without artist
        track1 = Track(
            track_number=1,
            title="Song Title",
            filename="song.mp3",
            file_path="/music/song.mp3"
        )
        
        assert track1.get_display_name() == "Song Title"
        
        # Track with artist
        track2 = Track(
            track_number=1,
            title="Song Title",
            filename="song.mp3",
            file_path="/music/song.mp3",
            artist="Artist Name"
        )
        
        assert track2.get_display_name() == "Artist Name - Song Title"
    
    def test_track_from_file_factory(self):
        """Test domain factory method."""
        track = Track.from_file("/music/example.mp3", 3)
        
        assert track.track_number == 3
        assert track.title == "example"  # Stem of filename
        assert track.filename == "example.mp3"
        assert track.file_path == "/music/example.mp3"
    
    def test_track_validation_edge_cases(self):
        """Test track validation edge cases."""
        # Valid track with minimal data
        valid_track = Track(
            track_number=1,
            title="Valid",
            filename="valid.mp3",
            file_path="/valid.mp3"
        )
        assert valid_track.is_valid() is True
        
        # Invalid: zero track number
        invalid_track = Track(
            track_number=0,
            title="Invalid",
            filename="invalid.mp3",
            file_path="/invalid.mp3"
        )
        assert invalid_track.is_valid() is False
        
        # Invalid: whitespace-only title
        whitespace_track = Track(
            track_number=1,
            title="   ",  # Only whitespace
            filename="whitespace.mp3",
            file_path="/whitespace.mp3"
        )
        assert whitespace_track.is_valid() is False
        
        # Invalid: empty filename
        empty_filename_track = Track(
            track_number=1,
            title="Good Title",
            filename="",
            file_path="/good/path.mp3"
        )
        assert empty_filename_track.is_valid() is False
        
        # Invalid: empty file_path
        empty_path_track = Track(
            track_number=1,
            title="Good Title",
            filename="good.mp3",
            file_path=""
        )
        assert empty_path_track.is_valid() is False
    
    def test_track_duration_conversion(self):
        """Test duration conversion from milliseconds to seconds."""
        # Track with duration
        track_with_duration = Track(
            track_number=1,
            title="Timed Track",
            filename="timed.mp3",
            file_path="/timed.mp3",
            duration_ms=180500  # 3 minutes 0.5 seconds
        )
        assert track_with_duration.duration == 180.5
        
        # Track without duration
        track_no_duration = Track(
            track_number=1,
            title="No Time",
            filename="notime.mp3",
            file_path="/notime.mp3",
            duration_ms=None
        )
        assert track_no_duration.duration is None
    
    def test_track_number_property_alias(self):
        """Test number property alias for API compatibility."""
        track = Track(
            track_number=5,
            title="Test Track",
            filename="test.mp3",
            file_path="/test.mp3"
        )
        
        # Test getter
        assert track.number == 5
        
        # Test setter
        track.number = 10
        assert track.track_number == 10
        assert track.number == 10
    
    def test_track_string_representation(self):
        """Test track string representation."""
        track = Track(
            track_number=3,
            title="My Song",
            filename="mysong.mp3",
            file_path="/music/mysong.mp3"
        )
        
        assert str(track) == "3. My Song"


class TestPlaylistDomainEntity:
    """Test Playlist domain entity business logic."""
    
    def test_playlist_creation(self):
        """Test basic playlist creation."""
        playlist = Playlist(
            title="Test Playlist",
            description="A test playlist",
            id="playlist-123"
        )

        assert playlist.title == "Test Playlist"
        assert playlist.description == "A test playlist"
        assert playlist.id == "playlist-123"
        assert len(playlist.tracks) == 0
    
    def test_playlist_api_compatibility(self):
        """Test API compatibility properties."""
        playlist = Playlist(title="My Playlist")
        
        # Test title alias
        assert playlist.title == "My Playlist"
        
        playlist.title = "Updated Playlist"
        assert playlist.title == "Updated Playlist"
    
    def test_playlist_track_management_domain_behavior(self):
        """Test domain behavior for track management."""
        playlist = Playlist(title="Test Playlist")
        
        track1 = Track(
            track_number=1,
            title="Track 1",
            filename="track1.mp3",
            file_path="/music/track1.mp3"
        )
        
        track2 = Track(
            track_number=2,
            title="Track 2",
            filename="track2.mp3",
            file_path="/music/track2.mp3"
        )
        
        # Test add track domain behavior
        playlist.add_track(track1)
        playlist.add_track(track2)
        
        assert len(playlist.tracks) == 2
        assert playlist.tracks[0] == track1
        assert playlist.tracks[1] == track2
    
    def test_playlist_auto_number_business_rule(self):
        """Test business rule: auto-assign track numbers."""
        playlist = Playlist(title="Test Playlist")
        
        # Track with number 0 should be auto-assigned
        track = Track(
            track_number=0,
            title="Auto Number Track",
            filename="auto.mp3",
            file_path="/music/auto.mp3"
        )
        
        playlist.add_track(track)
        
        # Should be auto-assigned number 1
        assert track.track_number == 1
    
    def test_playlist_validation_business_rule(self):
        """Test domain business rule: playlist validation."""
        # Valid playlist
        valid_playlist = Playlist(title="Valid Playlist")
        valid_track = Track(
            track_number=1,
            title="Valid Track",
            filename="valid.mp3",
            file_path="/music/valid.mp3"
        )
        valid_playlist.add_track(valid_track)
        
        assert valid_playlist.is_valid() is True
        
        # Invalid playlist: empty name
        invalid_playlist = Playlist(title="")
        assert invalid_playlist.is_valid() is False
        
        # Invalid playlist: contains invalid track
        invalid_playlist2 = Playlist(title="Invalid Playlist")
        invalid_track = Track(
            track_number=-1,
            title="",
            filename="",
            file_path=""
        )
        invalid_playlist2.add_track(invalid_track)
        
        assert invalid_playlist2.is_valid() is False
    
    def test_playlist_domain_services(self):
        """Test domain services for playlist operations."""
        playlist = Playlist(title="Service Test Playlist")
        
        track1 = Track(track_number=1, title="Track 1", filename="t1.mp3", file_path="/t1.mp3")
        track2 = Track(track_number=2, title="Track 2", filename="t2.mp3", file_path="/t2.mp3")
        
        playlist.add_track(track1)
        playlist.add_track(track2)
        
        # Test domain services
        assert playlist.is_empty() is False
        assert playlist.get_first_track() == track1
        assert playlist.get_track_by_position(1) == track2
        assert playlist.has_track_number(1) is True
        assert playlist.has_track_number(99) is False
        assert playlist.get_min_track_number() == 1
        assert playlist.get_max_track_number() == 2
    
    def test_playlist_normalization_business_rule(self):
        """Test business rule: track number normalization."""
        playlist = Playlist(title="Normalize Test")
        
        # Add tracks with non-sequential numbers
        track1 = Track(track_number=5, title="Track 5", filename="t5.mp3", file_path="/t5.mp3")
        track2 = Track(track_number=3, title="Track 3", filename="t3.mp3", file_path="/t3.mp3")
        track3 = Track(track_number=8, title="Track 8", filename="t8.mp3", file_path="/t8.mp3")
        
        playlist.add_track(track1)
        playlist.add_track(track2)
        playlist.add_track(track3)
        
        # Normalize should make them 1, 2, 3
        playlist.normalize_track_numbers()
        
        numbers = [track.track_number for track in playlist.tracks]
        assert numbers == [1, 2, 3]
    
    def test_playlist_duration_calculation_domain_service(self):
        """Test domain service: total duration calculation."""
        playlist = Playlist(title="Duration Test")
        
        track1 = Track(track_number=1, title="Track 1", filename="t1.mp3", 
                      file_path="/t1.mp3", duration_ms=180000)  # 3 minutes
        track2 = Track(track_number=2, title="Track 2", filename="t2.mp3", 
                      file_path="/t2.mp3", duration_ms=240000)  # 4 minutes
        
        playlist.add_track(track1)
        playlist.add_track(track2)
        
        total_duration = playlist.get_total_duration_ms()
        assert total_duration == 420000  # 7 minutes total
    
    def test_playlist_from_files_factory(self):
        """Test domain factory method."""
        file_paths = ["/music/song1.mp3", "/music/song2.mp3", "/music/song3.mp3"]
        
        playlist = Playlist.from_files("Factory Test", file_paths, description="Created by factory")
        
        assert playlist.title == "Factory Test"
        assert playlist.description == "Created by factory"
        assert len(playlist.tracks) == 3
        assert playlist.tracks[0].title == "song1"
        assert playlist.tracks[1].title == "song2"
        assert playlist.tracks[2].title == "song3"
    
    def test_playlist_display_name_domain_service(self):
        """Test domain service for display name formatting."""
        # Empty playlist
        empty_playlist = Playlist(title="Empty")
        assert empty_playlist.get_display_name() == "Empty (empty)"
        
        # Playlist with tracks
        playlist = Playlist(title="My Songs")
        track = Track(track_number=1, title="Song", filename="song.mp3", file_path="/song.mp3")
        playlist.add_track(track)
        
        assert playlist.get_display_name() == "My Songs (1 tracks)"
    
    def test_playlist_reordering_edge_cases(self):
        """Test edge cases for playlist reordering methods."""
        playlist = Playlist(title="Reorder Test")
        
        # Test empty playlist methods
        assert playlist.get_track_numbers() == []
        assert playlist.get_min_track_number() is None
        assert playlist.get_max_track_number() is None
        assert playlist.has_track_number(1) is False
        
        # Test with single track
        track = Track(track_number=5, title="Single", filename="single.mp3", file_path="/single.mp3")
        playlist.add_track(track)
        
        assert playlist.get_track_numbers() == [5]
        assert playlist.get_min_track_number() == 5
        assert playlist.get_max_track_number() == 5
        assert playlist.has_track_number(5) is True
        assert playlist.has_track_number(1) is False
    
    def test_playlist_normalize_empty_behavior(self):
        """Test normalize behavior on empty playlist."""
        playlist = Playlist(title="Empty Normalize")
        
        # Should not crash on empty playlist
        playlist.normalize_track_numbers()
        assert len(playlist.tracks) == 0
    
    def test_playlist_get_track_by_position_edge_cases(self):
        """Test get_track_by_position edge cases."""
        playlist = Playlist(title="Position Test")
        
        # Empty playlist
        assert playlist.get_track_by_position(0) is None
        assert playlist.get_track_by_position(-1) is None
        
        # Add tracks
        track1 = Track(track_number=1, title="Track 1", filename="t1.mp3", file_path="/t1.mp3")
        track2 = Track(track_number=2, title="Track 2", filename="t2.mp3", file_path="/t2.mp3")
        playlist.add_track(track1)
        playlist.add_track(track2)
        
        # Valid positions
        assert playlist.get_track_by_position(0) == track1
        assert playlist.get_track_by_position(1) == track2
        
        # Out of bounds
        assert playlist.get_track_by_position(2) is None
        assert playlist.get_track_by_position(-1) is None
    
    def test_playlist_total_duration_edge_cases(self):
        """Test total duration calculation edge cases."""
        playlist = Playlist(title="Duration Test")
        
        # Empty playlist should have 0 duration
        assert playlist.get_total_duration_ms() == 0
        
        # Tracks with unknown duration
        track1 = Track(track_number=1, title="Track 1", filename="t1.mp3", file_path="/t1.mp3", duration_ms=None)
        track2 = Track(track_number=2, title="Track 2", filename="t2.mp3", file_path="/t2.mp3", duration_ms=180000)
        playlist.add_track(track1)
        playlist.add_track(track2)
        
        # Should return None if any track has unknown duration
        assert playlist.get_total_duration_ms() is None
        
        # All tracks with known duration
        track1.duration_ms = 120000
        assert playlist.get_total_duration_ms() == 300000