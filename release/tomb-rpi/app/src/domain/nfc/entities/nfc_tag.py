# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Tag Domain Entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..value_objects.tag_identifier import TagIdentifier


@dataclass
class NfcTag:
    """Domain entity representing an NFC tag.

    Encapsulates NFC tag business logic and state management.
    """

    identifier: TagIdentifier
    associated_playlist_id: Optional[str] = None
    last_detected_at: Optional[datetime] = None
    detection_count: int = 0
    metadata: dict = field(default_factory=dict)

    def associate_with_playlist(self, playlist_id: str) -> None:
        """Associate this tag with a playlist.

        Args:
            playlist_id: Playlist identifier to associate

        Raises:
            ValueError: If playlist_id is invalid
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")

        self.associated_playlist_id = playlist_id

    def dissociate_from_playlist(self) -> None:
        """Remove playlist association from this tag."""
        self.associated_playlist_id = None

    def is_associated(self) -> bool:
        """Check if tag is associated with a playlist."""
        return self.associated_playlist_id is not None

    def mark_detected(self) -> None:
        """Mark this tag as detected, updating counters and timestamp."""
        self.last_detected_at = datetime.now(timezone.utc)
        self.detection_count += 1

    def is_recently_detected(self, seconds: int = 30) -> bool:
        """Check if tag was detected recently.

        Args:
            seconds: Time window to consider "recent"

        Returns:
            True if detected within the time window
        """
        if not self.last_detected_at:
            return False

        time_diff = datetime.now(timezone.utc) - self.last_detected_at
        return time_diff.total_seconds() <= seconds

    def get_associated_playlist_id(self) -> Optional[str]:
        """Get the associated playlist ID if any."""
        return self.associated_playlist_id

    def __eq__(self, other) -> bool:
        """Tags are equal if they have the same identifier."""
        if not isinstance(other, NfcTag):
            return False
        return self.identifier == other.identifier

    def __hash__(self) -> int:
        """Hash based on identifier for use in sets/dicts."""
        return hash(self.identifier)
