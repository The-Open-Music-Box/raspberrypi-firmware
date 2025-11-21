"""
Comprehensive tests for TrackReorderingService domain service.

Tests cover:
- Command validation
- Reordering strategies (bulk, swap, move)
- New order calculation
- Track creation after reordering
- Business rule enforcement
- Edge cases and error handling
"""

import pytest
from app.src.domain.services.track_reordering_service import (
    TrackReorderingService,
    ReorderingCommand,
    ReorderingStrategy,
    ReorderingResult
)
from app.src.domain.data.models.track import Track
from app.src.domain.data.models.playlist import Playlist


@pytest.fixture
def service():
    """Create a track reordering service instance."""
    return TrackReorderingService()


@pytest.fixture
def sample_tracks():
    """Create sample tracks for testing."""
    return [
        Track(track_number=1, title="Track 1", filename="t1.mp3", file_path="/t1.mp3", id="id1"),
        Track(track_number=2, title="Track 2", filename="t2.mp3", file_path="/t2.mp3", id="id2"),
        Track(track_number=3, title="Track 3", filename="t3.mp3", file_path="/t3.mp3", id="id3"),
        Track(track_number=4, title="Track 4", filename="t4.mp3", file_path="/t4.mp3", id="id4"),
    ]


class TestCommandValidation:
    """Test reordering command validation."""

    def test_validate_empty_playlist(self, service):
        """Test validation fails for empty playlist."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[1, 2, 3]
        )

        errors = service.validate_reordering_command(command, [])

        assert len(errors) > 0
        assert any("empty playlist" in err.lower() for err in errors)

    def test_validate_negative_track_numbers(self, service, sample_tracks):
        """Test validation fails for negative track numbers."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[-1, 2, 3, 4]
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("positive" in err.lower() for err in errors)

    def test_validate_zero_track_numbers(self, service, sample_tracks):
        """Test validation fails for zero track numbers."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[0, 1, 2, 3]
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("positive" in err.lower() for err in errors)

    def test_validate_duplicate_track_numbers(self, service, sample_tracks):
        """Test validation fails for duplicate track numbers."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[1, 2, 2, 3]
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("duplicate" in err.lower() for err in errors)

    def test_validate_nonexistent_track_numbers(self, service, sample_tracks):
        """Test validation fails for non-existent track numbers."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[1, 2, 99, 100]
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("do not exist" in err.lower() for err in errors)

    def test_validate_bulk_reorder_incomplete(self, service, sample_tracks):
        """Test bulk reorder validation fails if not all tracks included."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[1, 2]  # Missing 3 and 4
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("must include all tracks" in err.lower() for err in errors)

    def test_validate_target_positions_count_mismatch(self, service, sample_tracks):
        """Test validation fails when target positions count doesn't match."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.MOVE_TO_POSITION,
            track_numbers=[1, 2],
            target_positions=[1]  # Count mismatch
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("must match" in err.lower() for err in errors)

    def test_validate_invalid_target_positions(self, service, sample_tracks):
        """Test validation fails for invalid target positions."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.MOVE_TO_POSITION,
            track_numbers=[1, 2],
            target_positions=[0, 99]  # Out of bounds
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) > 0
        assert any("invalid target positions" in err.lower() for err in errors)

    def test_validate_valid_command(self, service, sample_tracks):
        """Test validation passes for valid command."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[4, 3, 2, 1]
        )

        errors = service.validate_reordering_command(command, sample_tracks)

        assert len(errors) == 0


class TestCalculateNewOrder:
    """Test new order calculation for different strategies."""

    def test_calculate_bulk_reorder(self, service, sample_tracks):
        """Test bulk reorder calculation."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[4, 3, 2, 1]
        )

        new_order = service.calculate_new_order(command, sample_tracks)

        assert new_order == [4, 3, 2, 1]

    def test_calculate_swap_tracks(self, service, sample_tracks):
        """Test swap tracks calculation."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[1, 3]
        )

        new_order = service.calculate_new_order(command, sample_tracks)

        # Track 1 and 3 should be swapped
        assert new_order == [3, 2, 1, 4]

    def test_calculate_swap_adjacent_tracks(self, service, sample_tracks):
        """Test swapping adjacent tracks."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[2, 3]
        )

        new_order = service.calculate_new_order(command, sample_tracks)

        assert new_order == [1, 3, 2, 4]

    def test_calculate_swap_invalid_track_count(self, service, sample_tracks):
        """Test swap with wrong number of tracks raises error."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[1, 2, 3]  # Should be exactly 2
        )

        with pytest.raises(ValueError, match="exactly 2 track numbers"):
            service.calculate_new_order(command, sample_tracks)

    def test_calculate_move_to_position_as_bulk(self, service, sample_tracks):
        """Test move to position with all tracks acts as bulk reorder."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.MOVE_TO_POSITION,
            track_numbers=[2, 1, 4, 3]
        )

        new_order = service.calculate_new_order(command, sample_tracks)

        assert new_order == [2, 1, 4, 3]

    def test_calculate_unsupported_strategy(self, service, sample_tracks):
        """Test unsupported strategy raises error."""
        # Create a mock strategy that doesn't exist
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy="INVALID_STRATEGY",  # Invalid
            track_numbers=[1, 2, 3, 4]
        )

        with pytest.raises(ValueError, match="Unsupported reordering strategy"):
            service.calculate_new_order(command, sample_tracks)


class TestCreateReorderedTracks:
    """Test creating reordered tracks."""

    def test_create_reordered_tracks_reverse(self, service, sample_tracks):
        """Test creating tracks in reverse order."""
        new_order = [4, 3, 2, 1]

        reordered = service.create_reordered_tracks(new_order, sample_tracks)

        assert len(reordered) == 4
        assert reordered[0].track_number == 1
        assert reordered[0].title == "Track 4"
        assert reordered[1].track_number == 2
        assert reordered[1].title == "Track 3"
        assert reordered[2].track_number == 3
        assert reordered[2].title == "Track 2"
        assert reordered[3].track_number == 4
        assert reordered[3].title == "Track 1"

    def test_create_reordered_tracks_preserves_metadata(self, service, sample_tracks):
        """Test reordered tracks preserve all metadata."""
        # Add metadata to tracks
        sample_tracks[0].artist = "Artist 1"
        sample_tracks[0].album = "Album 1"
        sample_tracks[0].duration_ms = 180000

        new_order = [2, 1, 3, 4]
        reordered = service.create_reordered_tracks(new_order, sample_tracks)

        # Track that was #1 is now #2
        assert reordered[1].artist == "Artist 1"
        assert reordered[1].album == "Album 1"
        assert reordered[1].duration_ms == 180000

    def test_create_reordered_tracks_updates_positions(self, service, sample_tracks):
        """Test reordered tracks have sequential positions."""
        new_order = [3, 1, 4, 2]

        reordered = service.create_reordered_tracks(new_order, sample_tracks)

        # Positions should be sequential 1, 2, 3, 4
        assert [t.track_number for t in reordered] == [1, 2, 3, 4]

    def test_create_reordered_tracks_preserves_ids(self, service, sample_tracks):
        """Test reordered tracks preserve track IDs."""
        new_order = [4, 3, 2, 1]

        reordered = service.create_reordered_tracks(new_order, sample_tracks)

        assert reordered[0].id == "id4"
        assert reordered[1].id == "id3"
        assert reordered[2].id == "id2"
        assert reordered[3].id == "id1"


class TestExecuteReordering:
    """Test complete reordering execution."""

    def test_execute_valid_reordering(self, service, sample_tracks):
        """Test executing valid reordering command."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[4, 3, 2, 1]
        )

        result = service.execute_reordering(command, sample_tracks)

        assert result.success is True
        assert result.original_order == [1, 2, 3, 4]
        assert result.new_order == [4, 3, 2, 1]
        assert len(result.affected_tracks) == 4
        assert len(result.validation_errors) == 0
        assert len(result.business_rule_violations) == 0

    def test_execute_invalid_command(self, service, sample_tracks):
        """Test executing invalid command returns errors."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[1, 99]  # Non-existent track
        )

        result = service.execute_reordering(command, sample_tracks)

        assert result.success is False
        assert len(result.validation_errors) > 0
        assert result.original_order == result.new_order  # No change

    def test_execute_empty_playlist(self, service):
        """Test executing reordering on empty playlist."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=[]
        )

        result = service.execute_reordering(command, [])

        assert result.success is False
        assert len(result.validation_errors) > 0

    def test_execute_swap(self, service, sample_tracks):
        """Test executing swap command."""
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[1, 4]
        )

        result = service.execute_reordering(command, sample_tracks)

        assert result.success is True
        assert result.new_order == [4, 2, 3, 1]
        # Track positions should be 1, 2, 3, 4
        assert [t.track_number for t in result.affected_tracks] == [1, 2, 3, 4]
        # But the track IDs should be swapped
        assert result.affected_tracks[0].id == "id4"
        assert result.affected_tracks[3].id == "id1"


class TestBusinessRuleChecks:
    """Test business rule validation after reordering."""

    def test_check_business_rules_valid(self, service, sample_tracks):
        """Test business rules pass for valid reordering."""
        reordered = service.create_reordered_tracks([4, 3, 2, 1], sample_tracks)

        violations = service._check_business_rules(reordered, sample_tracks)

        assert len(violations) == 0

    def test_check_track_count_changed(self, service, sample_tracks):
        """Test business rule violation when track count changes."""
        # Create reordered list with only 3 tracks instead of 4
        reordered = service.create_reordered_tracks([3, 2, 1], sample_tracks[:3])

        violations = service._check_business_rules(reordered, sample_tracks)

        assert len(violations) > 0
        assert any("track count changed" in v.lower() for v in violations)

    def test_check_missing_tracks(self, service, sample_tracks):
        """Test business rule violation when tracks are missing."""
        # Create reordered list missing a track
        reordered = [
            Track(track_number=1, title="T1", filename="t1.mp3", file_path="/t1.mp3", id="id1"),
            Track(track_number=2, title="T2", filename="t2.mp3", file_path="/t2.mp3", id="id2"),
            Track(track_number=3, title="T3", filename="t3.mp3", file_path="/t3.mp3", id="id3"),
        ]

        violations = service._check_business_rules(reordered, sample_tracks)

        assert len(violations) > 0
        assert any("missing tracks" in v.lower() for v in violations)

    def test_check_unexpected_tracks_added(self, service, sample_tracks):
        """Test business rule violation when extra tracks added."""
        reordered = service.create_reordered_tracks([4, 3, 2, 1], sample_tracks)
        # Add extra track
        extra = Track(track_number=5, title="Extra", filename="e.mp3", file_path="/e.mp3", id="id-extra")
        reordered.append(extra)

        violations = service._check_business_rules(reordered, sample_tracks)

        assert len(violations) > 0
        assert any("track count changed" in v.lower() for v in violations)

    def test_check_non_sequential_numbers(self, service, sample_tracks):
        """Test business rule violation for non-sequential track numbers."""
        # Manually create tracks with gaps in numbering
        reordered = [
            Track(track_number=1, title="T1", filename="t1.mp3", file_path="/t1.mp3", id="id1"),
            Track(track_number=3, title="T2", filename="t2.mp3", file_path="/t2.mp3", id="id2"),  # Gap!
            Track(track_number=4, title="T3", filename="t3.mp3", file_path="/t3.mp3", id="id3"),
            Track(track_number=5, title="T4", filename="t4.mp3", file_path="/t4.mp3", id="id4"),
        ]

        violations = service._check_business_rules(reordered, sample_tracks)

        assert len(violations) > 0
        assert any("not sequential" in v.lower() for v in violations)

    def test_check_duplicate_track_numbers(self, service, sample_tracks):
        """Test business rule violation for duplicate track numbers."""
        reordered = [
            Track(track_number=1, title="T1", filename="t1.mp3", file_path="/t1.mp3", id="id1"),
            Track(track_number=2, title="T2", filename="t2.mp3", file_path="/t2.mp3", id="id2"),
            Track(track_number=2, title="T3", filename="t3.mp3", file_path="/t3.mp3", id="id3"),  # Duplicate!
            Track(track_number=4, title="T4", filename="t4.mp3", file_path="/t4.mp3", id="id4"),
        ]

        violations = service._check_business_rules(reordered, sample_tracks)

        assert len(violations) > 0
        assert any("duplicate" in v.lower() for v in violations)


class TestCanReorder:
    """Test playlist reordering capability check."""

    def test_can_reorder_valid_playlist(self, service):
        """Test can reorder valid playlist."""
        playlist = Playlist.from_files("Test", ["/s1.mp3", "/s2.mp3", "/s3.mp3"])

        can_reorder, reason = service.can_reorder(playlist)

        assert can_reorder is True
        assert reason == ""

    def test_can_reorder_none_playlist(self, service):
        """Test cannot reorder None playlist."""
        can_reorder, reason = service.can_reorder(None)

        assert can_reorder is False
        assert "does not exist" in reason.lower()

    def test_can_reorder_empty_playlist(self, service):
        """Test cannot reorder empty playlist."""
        playlist = Playlist(title="Empty")

        can_reorder, reason = service.can_reorder(playlist)

        assert can_reorder is False
        assert "empty" in reason.lower()

    def test_can_reorder_single_track(self, service):
        """Test cannot reorder single track playlist."""
        playlist = Playlist.from_files("Single", ["/song.mp3"])

        can_reorder, reason = service.can_reorder(playlist)

        assert can_reorder is False
        assert "single track" in reason.lower()

    def test_can_reorder_two_tracks(self, service):
        """Test can reorder playlist with two tracks."""
        playlist = Playlist.from_files("Two", ["/s1.mp3", "/s2.mp3"])

        can_reorder, reason = service.can_reorder(playlist)

        assert can_reorder is True
        assert reason == ""


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_reorder_large_playlist(self, service):
        """Test reordering very large playlist."""
        # Create 100 tracks
        tracks = [
            Track(track_number=i, title=f"Track {i}", filename=f"t{i}.mp3",
                  file_path=f"/t{i}.mp3", id=f"id{i}")
            for i in range(1, 101)
        ]

        # Reverse the order
        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.BULK_REORDER,
            track_numbers=list(range(100, 0, -1))
        )

        result = service.execute_reordering(command, tracks)

        assert result.success is True
        assert len(result.affected_tracks) == 100
        assert result.affected_tracks[0].id == "id100"
        assert result.affected_tracks[99].id == "id1"

    def test_reorder_tracks_with_metadata(self, service):
        """Test reordering preserves all metadata."""
        tracks = [
            Track(track_number=1, title="T1", filename="t1.mp3", file_path="/t1.mp3",
                  duration_ms=180000, artist="Artist 1", album="Album", id="id1"),
            Track(track_number=2, title="T2", filename="t2.mp3", file_path="/t2.mp3",
                  duration_ms=240000, artist="Artist 2", album="Album", id="id2"),
        ]

        command = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[1, 2]
        )

        result = service.execute_reordering(command, tracks)

        assert result.success is True
        # First track should now have Artist 2's metadata
        assert result.affected_tracks[0].artist == "Artist 2"
        assert result.affected_tracks[0].duration_ms == 240000
        # Second track should have Artist 1's metadata
        assert result.affected_tracks[1].artist == "Artist 1"
        assert result.affected_tracks[1].duration_ms == 180000

    def test_multiple_swaps_in_sequence(self, service, sample_tracks):
        """Test multiple swap operations in sequence."""
        # First swap
        command1 = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[1, 2]
        )
        result1 = service.execute_reordering(command1, sample_tracks)

        # Second swap on the result
        command2 = ReorderingCommand(
            playlist_id="pl1",
            strategy=ReorderingStrategy.SWAP_TRACKS,
            track_numbers=[3, 4]
        )
        result2 = service.execute_reordering(command2, result1.affected_tracks)

        assert result2.success is True
        # Final order should be [2, 1, 4, 3] in terms of original IDs
        assert result2.affected_tracks[0].id == "id2"
        assert result2.affected_tracks[1].id == "id1"
        assert result2.affected_tracks[2].id == "id4"
        assert result2.affected_tracks[3].id == "id3"
