"""
Track Reordering Domain Service

This service encapsulates the business logic for track reordering operations.
It ensures consistency, validates business rules, and maintains track order integrity.

Following DDD principles:
- Contains domain logic that doesn't naturally fit into a single entity
- Coordinates between multiple domain objects (Playlist, Track)
- Maintains business invariants and rules
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_service_errors


class ReorderingStrategy(Enum):
    """Strategies for track reordering operations."""

    MOVE_TO_POSITION = "move_to_position"
    SWAP_TRACKS = "swap_tracks"
    BULK_REORDER = "bulk_reorder"


@dataclass
class ReorderingCommand:
    """Command object for track reordering operations."""

    playlist_id: str
    strategy: ReorderingStrategy
    track_numbers: List[int]
    target_positions: Optional[List[int]] = None
    validation_rules: Optional[Dict[str, any]] = None


@dataclass
class ReorderingResult:
    """Result object for track reordering operations."""

    success: bool
    original_order: List[int]
    new_order: List[int]
    affected_tracks: List[Track]
    validation_errors: List[str]
    business_rule_violations: List[str]


class TrackReorderingService:
    """
    Domain service for track reordering operations.

    Responsibilities:
    - Validates reordering business rules
    - Ensures track order consistency
    - Coordinates complex reordering operations
    - Maintains playlist integrity
    """

    def __init__(self):
        """Initialize the track reordering service."""
        pass

    def validate_reordering_command(
        self, command: ReorderingCommand, tracks: List[Track]
    ) -> List[str]:
        """
        Validate a reordering command against business rules.

        Business Rules:
        1. Track numbers must exist in the playlist
        2. No duplicate track numbers in new order
        3. All track numbers must be positive integers
        4. Track count must remain consistent
        5. Playlist must not be empty

        Args:
            command: The reordering command to validate
            tracks: Current tracks in the playlist

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Rule 1: Playlist must not be empty
        if not tracks:
            errors.append("Cannot reorder tracks in empty playlist")
            return errors

        # Rule 2: Track numbers must be positive
        invalid_numbers = [num for num in command.track_numbers if num <= 0]
        if invalid_numbers:
            errors.append(f"Track numbers must be positive: {invalid_numbers}")

        # Rule 3: No duplicate track numbers
        if len(command.track_numbers) != len(set(command.track_numbers)):
            duplicates = [
                num for num in command.track_numbers if command.track_numbers.count(num) > 1
            ]
            errors.append(f"Duplicate track numbers not allowed: {set(duplicates)}")

        # Rule 4: Track numbers must exist
        existing_numbers = {track.track_number for track in tracks}
        invalid_tracks = [num for num in command.track_numbers if num not in existing_numbers]
        if invalid_tracks:
            errors.append(f"Track numbers do not exist in playlist: {invalid_tracks}")

        # Rule 5: Track count consistency
        if command.strategy == ReorderingStrategy.BULK_REORDER:
            if len(command.track_numbers) != len(tracks):
                errors.append(
                    f"Bulk reorder must include all tracks. "
                    f"Expected {len(tracks)}, got {len(command.track_numbers)}"
                )

        # Rule 6: Target positions validation (if provided)
        if command.target_positions:
            if len(command.target_positions) != len(command.track_numbers):
                errors.append("Target positions count must match track numbers count")

            invalid_positions = [
                pos for pos in command.target_positions if pos < 1 or pos > len(tracks)
            ]
            if invalid_positions:
                errors.append(
                    f"Invalid target positions (must be 1-{len(tracks)}): {invalid_positions}"
                )

        return errors

    def calculate_new_order(self, command: ReorderingCommand, tracks: List[Track]) -> List[int]:
        """
        Calculate the new track order based on the reordering command.

        Args:
            command: The reordering command
            tracks: Current tracks in the playlist

        Returns:
            List of track numbers in new order
        """
        if command.strategy == ReorderingStrategy.BULK_REORDER:
            return command.track_numbers.copy()

        elif command.strategy == ReorderingStrategy.MOVE_TO_POSITION:
            # More complex logic for moving specific tracks to positions
            current_order = [
                track.track_number for track in sorted(tracks, key=lambda t: t.track_number)
            ]
            new_order = current_order.copy()

            # For now, implement as bulk reorder (can be enhanced later)
            if len(command.track_numbers) == len(tracks):
                return command.track_numbers.copy()

            return new_order

        elif command.strategy == ReorderingStrategy.SWAP_TRACKS:
            if len(command.track_numbers) != 2:
                raise ValueError("Swap strategy requires exactly 2 track numbers")

            current_order = [
                track.track_number for track in sorted(tracks, key=lambda t: t.track_number)
            ]
            new_order = current_order.copy()

            # Find positions and swap
            track1, track2 = command.track_numbers
            pos1 = new_order.index(track1)
            pos2 = new_order.index(track2)
            new_order[pos1], new_order[pos2] = new_order[pos2], new_order[pos1]

            return new_order

        else:
            raise ValueError(f"Unsupported reordering strategy: {command.strategy}")

    def create_reordered_tracks(self, new_order: List[int], tracks: List[Track]) -> List[Track]:
        """
        Create a new list of tracks with updated track numbers based on new order.

        Args:
            new_order: List of track numbers in desired order
            tracks: Original tracks

        Returns:
            New list of tracks with updated track_number values
        """
        # Create lookup map for tracks by their current track number
        track_map = {track.track_number: track for track in tracks}

        # Create reordered list with updated track numbers
        reordered_tracks = []
        for position, original_track_number in enumerate(new_order, 1):
            original_track = track_map[original_track_number]

            # Create new track with updated position using the actual Track model
            updated_track = Track(
                track_number=position,  # New position
                title=original_track.title,
                filename=original_track.filename,
                file_path=original_track.file_path,
                duration_ms=original_track.duration_ms,
                artist=original_track.artist,
                album=original_track.album,
                id=original_track.id,
            )
            reordered_tracks.append(updated_track)

        return reordered_tracks

    @handle_service_errors("track_reordering")
    def execute_reordering(
        self, command: ReorderingCommand, tracks: List[Track]
    ) -> ReorderingResult:
        """
        Execute a track reordering operation.

        This is the main entry point for track reordering business logic.

        Args:
            command: The reordering command to execute
            tracks: Current tracks in the playlist

        Returns:
            ReorderingResult with operation details and any errors
        """
        # Store original order for rollback/audit purposes
        original_order = [
            track.track_number for track in sorted(tracks, key=lambda t: t.track_number)
        ]

        # Validate the command
        validation_errors = self.validate_reordering_command(command, tracks)
        if validation_errors:
            return ReorderingResult(
                success=False,
                original_order=original_order,
                new_order=original_order,  # No change
                affected_tracks=[],
                validation_errors=validation_errors,
                business_rule_violations=[],
            )

        # Calculate new order
        new_order = self.calculate_new_order(command, tracks)
        # Create reordered tracks
        reordered_tracks = self.create_reordered_tracks(new_order, tracks)
        # Check for business rule violations
        business_rule_violations = self._check_business_rules(reordered_tracks, tracks)
        if business_rule_violations:
            return ReorderingResult(
                success=False,
                original_order=original_order,
                new_order=original_order,
                affected_tracks=[],
                validation_errors=[],
                business_rule_violations=business_rule_violations,
            )
        return ReorderingResult(
            success=True,
            original_order=original_order,
            new_order=new_order,
            affected_tracks=reordered_tracks,
            validation_errors=[],
            business_rule_violations=[],
        )

    def _check_business_rules(
        self, reordered_tracks: List[Track], original_tracks: List[Track]
    ) -> List[str]:
        """
        Check business rules after reordering.

        Business Rules:
        1. Track count must remain the same
        2. All original tracks must still be present
        3. Track numbers must be sequential (1, 2, 3, ...)
        4. No duplicate track numbers

        Args:
            reordered_tracks: Tracks after reordering
            original_tracks: Original tracks before reordering

        Returns:
            List of business rule violations
        """
        violations = []

        # Rule 1: Track count consistency
        if len(reordered_tracks) != len(original_tracks):
            violations.append(
                f"Track count changed: {len(original_tracks)} -> {len(reordered_tracks)}"
            )

        # Rule 2: All original tracks present
        original_ids = {track.id for track in original_tracks}
        reordered_ids = {track.id for track in reordered_tracks}
        if original_ids != reordered_ids:
            missing = original_ids - reordered_ids
            added = reordered_ids - original_ids
            if missing:
                violations.append(f"Missing tracks: {missing}")
            if added:
                violations.append(f"Unexpected tracks added: {added}")

        # Rule 3: Sequential track numbers
        track_numbers = sorted(track.track_number for track in reordered_tracks)
        expected_numbers = list(range(1, len(reordered_tracks) + 1))
        if track_numbers != expected_numbers:
            violations.append(
                f"Track numbers not sequential. Expected: {expected_numbers}, Got: {track_numbers}"
            )

        # Rule 4: No duplicates
        if len(track_numbers) != len(set(track_numbers)):
            violations.append("Duplicate track numbers found")

        return violations

    def can_reorder(self, playlist: Playlist) -> Tuple[bool, str]:
        """
        Check if a playlist can be reordered.

        Args:
            playlist: The playlist to check

        Returns:
            Tuple of (can_reorder, reason_if_not)
        """
        if playlist is None:
            return False, "Playlist does not exist"

        if not playlist.tracks or len(playlist.tracks) == 0:
            return False, "Playlist is empty"

        if len(playlist.tracks) == 1:
            return False, "Single track playlist cannot be reordered"

        # Could add more business rules here:
        # - Check if playlist is locked
        # - Check user permissions
        # - Check if playlist is being played

        return True, ""
