# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Control event type enumeration.

This module defines the types of control events that can be triggered
by physical controls like buttons and rotary encoders.
"""

from enum import Enum


class ControlEventType(Enum):
    """Enumeration of control event types.

    Defines the different types of control events that can be triggered
    by physical hardware controls.
    """

    PLAY_PAUSE = "play_pause"
    NEXT_TRACK = "next_track"
    PREVIOUS_TRACK = "previous_track"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    STOP = "stop"
