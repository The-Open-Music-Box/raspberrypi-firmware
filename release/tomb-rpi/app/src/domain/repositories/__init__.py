# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Repository interfaces for the domain layer.

These define the contracts that infrastructure implementations must fulfill,
following the Dependency Inversion Principle of Domain-Driven Design.
"""

from .playlist_repository_interface import PlaylistRepositoryProtocol

__all__ = ["PlaylistRepositoryProtocol"]
