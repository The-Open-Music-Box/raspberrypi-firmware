# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Decorators Package

Provides reusable decorators for:
- API-specific error handling
- Rate limiting
- Dependency injection
- Request/response logging
"""

from .api_decorators import (
    with_rate_limiting,
    with_operation_tracking,
    with_request_logging,
)

__all__ = [
    "with_rate_limiting",
    "with_operation_tracking",
    "with_request_logging",
]
