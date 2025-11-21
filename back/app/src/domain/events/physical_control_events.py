# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Physical Control Events for Domain Layer.

Events triggered by physical hardware controls like buttons and encoders.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class ButtonPressedEvent:
    """Event triggered when a button is pressed."""
    button_type: str  # "next", "previous", "play_pause"
    timestamp: datetime
    source_pin: Optional[int] = None
    press_duration: Optional[float] = None  # Duration in seconds for long press detection


@dataclass
class EncoderRotatedEvent:
    """Event triggered when rotary encoder is rotated."""
    direction: str  # "up" or "down"
    timestamp: datetime
    source_pin: Optional[int] = None
    steps: int = 1  # Number of encoder steps


@dataclass
class PhysicalControlErrorEvent:
    """Event triggered when a physical control error occurs."""
    error_message: str
    error_type: str
    component: str
    timestamp: datetime
    source_pin: Optional[int] = None