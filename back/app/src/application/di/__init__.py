# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Application Layer Dependency Injection."""

from .application_container import get_application_container

__all__ = ["get_application_container"]