# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Domain actions package.

Contains action definitions for physical controls and other triggers.
"""

from .button_actions import (
    ButtonAction,
    PlayAction,
    PauseAction,
    PlayPauseAction,
    NextTrackAction,
    PreviousTrackAction,
    VolumeUpAction,
    VolumeDownAction,
    StopAction,
    PrintDebugAction,
)

__all__ = [
    "ButtonAction",
    "PlayAction",
    "PauseAction",
    "PlayPauseAction",
    "NextTrackAction",
    "PreviousTrackAction",
    "VolumeUpAction",
    "VolumeDownAction",
    "StopAction",
    "PrintDebugAction",
]
