# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain exceptions."""

from .data_exceptions import (
    DataDomainError,
    PlaylistNotFoundError,
    TrackNotFoundError,
    PlaylistValidationError,
    TrackValidationError
)

__all__ = [
    'DataDomainError',
    'PlaylistNotFoundError',
    'TrackNotFoundError',
    'PlaylistValidationError',
    'TrackValidationError'
]