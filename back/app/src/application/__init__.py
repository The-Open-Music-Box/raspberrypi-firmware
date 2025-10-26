# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Application layer for TheOpenMusicBox following Domain-Driven Design principles.

The application layer orchestrates domain operations and implements use cases.
It should not contain business logic (which belongs in the domain layer)
but coordinates domain operations and external services.

Structure:
- services/: Application services that coordinate domain operations
- commands/: Command handlers for write operations (CQRS pattern)
- queries/: Query handlers for read operations (CQRS pattern)
"""
