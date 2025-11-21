# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Tag Identifier Value Object."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TagIdentifier:
    """Value object representing an NFC tag identifier.

    Immutable identifier that encapsulates NFC tag validation logic.
    """

    uid: str

    def __post_init__(self):
        """Validate tag identifier on creation."""
        if not self.uid:
            raise ValueError("Tag UID cannot be empty")
        if len(self.uid) < 4:
            raise ValueError("Tag UID too short (minimum 4 characters)")
        if not all(c in "0123456789abcdefABCDEF" for c in self.uid):
            raise ValueError("Tag UID must be hexadecimal")

    @classmethod
    def from_raw_data(cls, raw_data: str) -> "TagIdentifier":
        """Create TagIdentifier from raw NFC data.

        Args:
            raw_data: Raw NFC tag data

        Returns:
            TagIdentifier instance
        """
        # Normalize UID (remove spaces, convert to lowercase)
        uid = raw_data.replace(" ", "").replace(":", "").lower()
        return cls(uid=uid)

    def is_valid(self) -> bool:
        """Check if this tag identifier is valid."""
        try:
            self.__post_init__()
            return True
        except ValueError:
            return False

    def __str__(self) -> str:
        """String representation of tag identifier."""
        return self.uid
