# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Pure DDD Database Infrastructure Module

This module contains database infrastructure components following DDD principles:
- SQLiteDatabaseService: Pure infrastructure implementation of PersistenceServiceProtocol
- Clean separation between domain protocols and infrastructure implementations
"""

from .sqlite_database_service import SQLiteDatabaseService

__all__ = ["SQLiteDatabaseService"]