# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain protocols."""

from .repository_protocol import (
    PlaylistRepositoryProtocol,
    TrackRepositoryProtocol
)
from .service_protocol import (
    PlaylistServiceProtocol,
    TrackServiceProtocol
)

__all__ = [
    'PlaylistRepositoryProtocol',
    'TrackRepositoryProtocol',
    'PlaylistServiceProtocol',
    'TrackServiceProtocol'
]