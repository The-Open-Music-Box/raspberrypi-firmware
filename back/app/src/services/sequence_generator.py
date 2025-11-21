# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Sequence Number Generator

Thread-safe sequence number generation for event ordering and synchronization.
Extracted from StateManager for better separation of concerns.
"""

import asyncio
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class SequenceGenerator:
    """
    Thread-safe sequence number generator for events.

    Provides both global sequences and playlist-specific sequences
    for proper event ordering and client synchronization.
    """

    def __init__(self):
        self._global_seq = 0
        self._playlist_sequences: Dict[str, int] = {}

        # Thread safety locks
        self._global_lock = asyncio.Lock()
        self._playlist_lock = asyncio.Lock()

        logger.info("SequenceGenerator initialized")

    async def get_next_global_seq(self) -> int:
        """Get the next global sequence number with thread safety."""
        async with self._global_lock:
            self._global_seq += 1
            return self._global_seq

    async def get_next_playlist_seq(self, playlist_id: str) -> int:
        """Get the next sequence number for a specific playlist with thread safety."""
        async with self._playlist_lock:
            if playlist_id not in self._playlist_sequences:
                self._playlist_sequences[playlist_id] = 0
            self._playlist_sequences[playlist_id] += 1
            return self._playlist_sequences[playlist_id]

    def get_current_global_seq(self) -> int:
        """Get current global sequence number (read-only, no increment)."""
        return self._global_seq

    def get_current_playlist_seq(self, playlist_id: str) -> int:
        """Get current sequence number for a playlist (read-only, no increment)."""
        return self._playlist_sequences.get(playlist_id, 0)

    def reset_global_seq(self, value: int = 0) -> None:
        """Reset global sequence to a specific value (for testing/recovery)."""
        self._global_seq = value
        logger.info(f"Global sequence reset to {value}")

    def reset_playlist_seq(self, playlist_id: str, value: int = 0) -> None:
        """Reset playlist sequence to a specific value (for testing/recovery)."""
        self._playlist_sequences[playlist_id] = value
        logger.info(f"Playlist {playlist_id} sequence reset to {value}")

    def get_all_playlist_sequences(self) -> Dict[str, int]:
        """Get all playlist sequences (read-only copy)."""
        return self._playlist_sequences.copy()

    def get_stats(self) -> dict:
        """Get sequence statistics for monitoring."""
        return {
            "global_sequence": self._global_seq,
            "tracked_playlists": len(self._playlist_sequences),
            "playlist_sequences": self._playlist_sequences.copy(),
            "highest_playlist_seq": (
                max(self._playlist_sequences.values()) if self._playlist_sequences else 0
            ),
        }
