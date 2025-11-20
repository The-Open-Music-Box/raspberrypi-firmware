# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Database migrations module."""

from .migration_runner import Migration, MigrationRunner

__all__ = ["Migration", "MigrationRunner"]
