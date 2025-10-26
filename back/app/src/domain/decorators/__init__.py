# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Domain layer decorators."""

from .error_handler import handle_domain_errors

__all__ = ["handle_domain_errors"]