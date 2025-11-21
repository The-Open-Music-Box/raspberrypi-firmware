# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Base Controls Implementation.

Provides common functionality for physical controls implementations,
extracting duplication between GPIOPhysicalControls and MockPhysicalControls.
Follows Context7 principles with proper type safety and DDD architecture.
"""

from typing import Callable, Dict, List, Optional, Any
from abc import abstractmethod
import logging

from app.src.domain.protocols.physical_controls_protocol import (
    PhysicalControlsProtocol,
    PhysicalControlEvent,
)
from app.src.config.button_actions_config import ButtonActionConfig, DEFAULT_BUTTON_CONFIGS

logger = logging.getLogger(__name__)


class BaseControlsImplementation(PhysicalControlsProtocol):
    """
    Base class for physical controls implementations.

    This class provides common functionality for physical controls, including:
    - State management (_is_initialized, _event_handlers, _button_configs)
    - Event handler registration and invocation
    - Common initialization checks
    - Button configuration management

    Subclasses must implement:
    - initialize(): Hardware-specific initialization
    - cleanup(): Hardware-specific cleanup
    - get_status(): Hardware-specific status reporting
    """

    def __init__(
        self,
        hardware_config: Any,
        button_configs: Optional[List[ButtonActionConfig]] = None
    ):
        """Initialize base controls state.

        Extracted common initialization from GPIOPhysicalControls and MockPhysicalControls.
        This pattern was duplicated identically (9 lines at GPIO:98-106, Mock:25-35).

        Args:
            hardware_config: Hardware configuration
            button_configs: Optional button configurations (uses DEFAULT_BUTTON_CONFIGS if None)
        """
        self.config = hardware_config
        self._button_configs = button_configs or DEFAULT_BUTTON_CONFIGS
        self._is_initialized = False
        self._event_handlers: Dict[PhysicalControlEvent, Callable[[], None]] = {}

        logger.debug(f"{self.__class__.__name__}: Base controls state initialized")

    def set_event_handler(
        self,
        event_type: PhysicalControlEvent,
        handler: Callable[[], None]
    ) -> None:
        """Set event handler for a specific control event.

        Common implementation identical in both implementations.
        Extracted to eliminate duplication (5 lines at GPIO:442-446, Mock:51-54).

        Args:
            event_type: Type of physical control event
            handler: Callback function to handle the event
        """
        self._event_handlers[event_type] = handler
        logger.debug(f"{self.__class__.__name__}: Event handler set for {event_type}")

    def is_initialized(self) -> bool:
        """Check if controls are initialized.

        Common implementation identical in both implementations.
        Extracted to eliminate duplication.

        Returns:
            bool: True if initialized, False otherwise
        """
        return self._is_initialized

    def _invoke_event_handler(
        self,
        event_type: PhysicalControlEvent,
        operation_name: str = "event"
    ) -> None:
        """Invoke event handler for a specific event type.

        Extracted helper to eliminate duplication of event handler invocation logic.
        This pattern appears in both implementations (13 lines at GPIO:98-110, Mock:94-102).

        Args:
            event_type: Type of event to handle
            operation_name: Name of the operation for logging
        """
        handler = self._event_handlers.get(event_type)
        if handler:
            logger.debug(f"{self.__class__.__name__}: Invoking {operation_name} handler for {event_type}")
            try:
                handler()
            except Exception as e:
                logger.error(
                    f"❌ {self.__class__.__name__}: Error in {operation_name} handler "
                    f"for {event_type}: {e}"
                )
        else:
            logger.debug(
                f"{self.__class__.__name__}: No handler registered for {event_type}"
            )

    def _build_button_info(self) -> Dict[str, Any]:
        """Build button configuration information for status reporting.

        Extracted helper to eliminate duplication of button info building logic.
        This pattern appears identically in both implementations.

        Returns:
            Dictionary with button configuration information
        """
        button_info = {}
        for config in self._button_configs:
            if config.enabled:
                button_info[f"button_{config.button_id}"] = {
                    "gpio_pin": config.gpio_pin,
                    "action": config.action_name,
                    "description": config.description,
                }
        return button_info

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize hardware controls.

        Must be implemented by subclasses for hardware-specific initialization.
        - Mock: Simple flag setting and logging
        - GPIO: Device initialization with error handling

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up hardware resources.

        Must be implemented by subclasses for hardware-specific cleanup.
        - Mock: Reset state and clear handlers
        - GPIO: Cleanup GPIO devices and release resources
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current status of controls.

        Must be implemented by subclasses for hardware-specific status info.
        - Mock: Include mock_mode flag
        - GPIO: Include GPIO device information

        Returns:
            Dictionary with status information
        """
        pass
