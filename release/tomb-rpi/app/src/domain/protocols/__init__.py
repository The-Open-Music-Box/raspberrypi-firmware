# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Domain protocols for type-safe dependency injection.

This package contains protocol definitions that establish contracts
between domain services and their implementations, promoting loose
coupling and improved testability.
"""

from .audio_backend_protocol import AudioBackendProtocol
from .audio_engine_protocol import AudioEngineProtocol
from .audio_service_protocol import AudioServiceProtocol
from .event_bus_protocol import EventBusProtocol
from .nfc_protocol import NFCServiceProtocol, NFCHardwareProtocol
from .state_manager_protocol import StateManagerProtocol

__all__ = [
    "AudioBackendProtocol",
    "AudioEngineProtocol",
    "AudioServiceProtocol",
    "EventBusProtocol",
    "NFCServiceProtocol",
    "NFCHardwareProtocol",
    "StateManagerProtocol",
]
