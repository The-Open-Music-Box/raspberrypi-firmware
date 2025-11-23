# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Base Domain Service

Provides common patterns for domain services to eliminate duplication.
Single Responsibility: Reusable domain service functionality.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import asdict


class BaseDomainService:
    """
    Base class for domain services with common validation and transformation patterns.

    Single Responsibility: Provide reusable patterns for domain services.
    Eliminates duplication of validation, transformation, and logging patterns.
    """

    def __init__(self):
        """Initialize base domain service with logger."""
        self._logger = logging.getLogger(self.__class__.__name__)

    def _validate_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: List[str]
    ) -> Optional[str]:
        """
        Common validation logic for required fields.

        Args:
            data: Data dictionary to validate
            required_fields: List of required field names

        Returns:
            Error message if validation fails, None otherwise
        """
        missing = [f for f in required_fields if f not in data or not data[f]]
        if missing:
            return f"Missing required fields: {', '.join(missing)}"
        return None

    def _transform_with_defaults(
        self,
        data: Dict[str, Any],
        defaults: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Common transformation logic combining data with defaults.

        Args:
            data: Source data dictionary
            defaults: Default values dictionary

        Returns:
            Merged dictionary with defaults + data
        """
        result = defaults.copy()
        result.update(data)
        return result

    async def _execute_with_logging(
        self,
        operation: Callable,
        operation_name: str,
        context: Dict[str, Any]
    ) -> Any:
        """
        Common execution pattern with logging for domain operations.

        Args:
            operation: Async callable to execute
            operation_name: Name for logging
            context: Context data for logging

        Returns:
            Result from operation

        Raises:
            Re-raises any exception from operation after logging
        """
        self._logger.info(f"Starting {operation_name}", extra=context)
        try:
            result = await operation()
            self._logger.info(f"Completed {operation_name}", extra=context)
            return result
        except Exception as e:
            self._logger.error(f"Failed {operation_name}: {e}", extra=context)
            raise

    def _convert_entity_to_dict_with_track_count(
        self,
        entity: Any,
        track_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Common pattern for converting playlist entities to dicts with track count.

        This pattern appears 4 times in PlaylistService:
        - get_playlists (lines 62-67)
        - get_playlist (lines 93-98)
        - create_playlist (lines 126-130)
        - get_playlist_by_nfc (lines 263-267)

        Args:
            entity: Domain entity with tracks attribute
            track_count: Optional track count (if not provided, calculates from entity.tracks)

        Returns:
            Dictionary with track_count and title field compatibility
        """
        playlist_dict = asdict(entity)

        # Add track count
        if track_count is not None:
            playlist_dict['track_count'] = track_count
        elif hasattr(entity, 'tracks'):
            playlist_dict['track_count'] = len(entity.tracks)
        else:
            playlist_dict['track_count'] = 0

        # Ensure title field exists (for API compatibility)
        if 'title' not in playlist_dict and 'name' in playlist_dict:
            playlist_dict['title'] = playlist_dict['name']

        return playlist_dict

    def _find_track_index(
        self,
        tracks: List[Any],
        track_id: str
    ) -> Optional[int]:
        """
        Common pattern for finding track index by ID.

        This pattern appears 2 times in TrackService:
        - get_next_track (lines 233-239)
        - get_previous_track (lines 275-281)

        Args:
            tracks: List of track entities or dictionaries
            track_id: Track ID to find

        Returns:
            Index of track or None if not found
        """
        for i, track in enumerate(tracks):
            current_track_id = track.id if hasattr(track, 'id') else track['id']
            if current_track_id == track_id:
                return i
        return None
