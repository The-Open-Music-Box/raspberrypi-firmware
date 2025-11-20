# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Core package for the music box application."""

__version__ = "0.1.0"
__app_name__ = "TheOpenMusicBox"
__author__ = "Jonathan Piette"


from .helpers import AppError

__all__ = ["AppError", "__version__", "__app_name__", "__author__"]
