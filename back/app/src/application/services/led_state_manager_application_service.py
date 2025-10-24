# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
LED State Manager (Application Layer).

Manages LED indicator states with priority-based stack and automatic timeout handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Lock

from app.src.domain.protocols.indicator_lights_protocol import IndicatorLightsProtocol
from app.src.domain.models.led import (
    LEDState,
    LEDStateConfig,
    LEDColor,
    LEDAnimation,
    DEFAULT_LED_STATE_CONFIGS
)

logger = logging.getLogger(__name__)


@dataclass
class ActiveLEDState:
    """Represents an active LED state with timeout tracking."""
    config: LEDStateConfig
    activated_at: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """Check if this state has expired based on its timeout."""
        if self.config.timeout_seconds is None:
            return False

        elapsed = (datetime.now() - self.activated_at).total_seconds()
        return elapsed >= self.config.timeout_seconds

    def time_remaining(self) -> Optional[float]:
        """Get remaining time in seconds, or None if no timeout."""
        if self.config.timeout_seconds is None:
            return None

        elapsed = (datetime.now() - self.activated_at).total_seconds()
        remaining = self.config.timeout_seconds - elapsed
        return max(0.0, remaining)


class LEDStateManager:
    """
    Manages LED indicator states with priority-based stack.

    Features:
    - Priority-based state stack (higher priority overrides lower)
    - Automatic timeout management for temporary states
    - Thread-safe state transitions
    - Integration with hardware LED controller

    State Management Rules:
    - New states are pushed onto the stack by priority
    - Highest priority state is always displayed
    - When a state expires, it's removed and next highest is displayed
    - Permanent states (no timeout) remain until explicitly cleared
    """

    def __init__(
        self,
        led_controller: IndicatorLightsProtocol,
        state_configs: Optional[Dict[LEDState, LEDStateConfig]] = None
    ):
        """
        Initialize LED state manager.

        Args:
            led_controller: Hardware LED controller implementation
            state_configs: Optional custom state configurations (defaults to DEFAULT_LED_STATE_CONFIGS)
        """
        self._led_controller = led_controller
        self._state_configs = state_configs or DEFAULT_LED_STATE_CONFIGS

        # State stack (sorted by priority, highest first)
        self._state_stack: List[ActiveLEDState] = []
        self._lock = Lock()

        # Timeout monitoring
        self._timeout_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Current displayed state tracking
        self._current_displayed_state: Optional[LEDState] = None

    async def initialize(self) -> bool:
        """
        Initialize LED state manager and hardware controller.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize hardware controller
            success = await self._led_controller.initialize()
            if not success:
                logger.error("Failed to initialize LED controller")
                return False

            # Start timeout monitoring task
            self._is_running = True
            self._timeout_task = asyncio.create_task(self._timeout_monitor_loop())

            # Set initial state to IDLE
            await self.set_state(LEDState.IDLE)

            logger.info("✅ LED state manager initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize LED state manager: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up resources and turn off LED."""
        try:
            logger.info("🧹 Cleaning up LED state manager...")

            # Stop timeout monitoring
            self._is_running = False
            if self._timeout_task:
                self._timeout_task.cancel()
                try:
                    await self._timeout_task
                except asyncio.CancelledError:
                    pass

            # Clear all states
            with self._lock:
                self._state_stack.clear()
                self._current_displayed_state = None

            # Clean up hardware
            await self._led_controller.cleanup()

            logger.info("✅ LED state manager cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during LED state manager cleanup: {e}")

    async def set_state(self, state: LEDState) -> bool:
        """
        Set a new LED state.

        The state will be added to the priority stack. If it has higher priority
        than the current displayed state, it will be displayed immediately.

        Args:
            state: LED state to set

        Returns:
            True if state was set successfully, False otherwise
        """
        try:
            # Get state configuration
            config = self._state_configs.get(state)
            if not config:
                logger.warning(f"No configuration found for state: {state}")
                return False

            with self._lock:
                # Remove any existing instances of this state
                self._state_stack = [s for s in self._state_stack if s.config.state != state]

                # Create new active state
                active_state = ActiveLEDState(config=config)

                # Insert into stack by priority (highest first)
                inserted = False
                for i, existing in enumerate(self._state_stack):
                    if config.priority > existing.config.priority:
                        self._state_stack.insert(i, active_state)
                        inserted = True
                        break

                if not inserted:
                    self._state_stack.append(active_state)

                logger.info(
                    f"LED state set: {state.value} (priority {config.priority}, "
                    f"timeout: {config.timeout_seconds}s)"
                )

            # Update display to show highest priority state
            await self._update_display()

            return True

        except Exception as e:
            logger.error(f"❌ Error setting LED state {state}: {e}")
            return False

    async def clear_state(self, state: LEDState) -> bool:
        """
        Clear a specific LED state from the stack.

        Args:
            state: LED state to clear

        Returns:
            True if state was cleared, False otherwise
        """
        try:
            with self._lock:
                original_len = len(self._state_stack)
                self._state_stack = [s for s in self._state_stack if s.config.state != state]
                removed = len(self._state_stack) < original_len

            if removed:
                logger.info(f"LED state cleared: {state.value}")
                await self._update_display()
                return True
            else:
                logger.debug(f"LED state not in stack: {state.value}")
                return False

        except Exception as e:
            logger.error(f"❌ Error clearing LED state {state}: {e}")
            return False

    async def clear_all_states(self) -> bool:
        """
        Clear all LED states and turn off LED.

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                self._state_stack.clear()
                self._current_displayed_state = None

            await self._led_controller.turn_off()

            logger.info("All LED states cleared")
            return True

        except Exception as e:
            logger.error(f"❌ Error clearing all LED states: {e}")
            return False

    async def _update_display(self) -> None:
        """Update LED hardware to display highest priority state."""
        try:
            # Get highest priority state
            highest_priority_state = None
            with self._lock:
                if self._state_stack:
                    highest_priority_state = self._state_stack[0]

            # If no states, turn off LED
            if not highest_priority_state:
                if self._current_displayed_state is not None:
                    await self._led_controller.turn_off()
                    self._current_displayed_state = None
                    logger.debug("LED turned off (no active states)")
                return

            config = highest_priority_state.config

            # Only update if state changed
            if self._current_displayed_state != config.state:
                # Set LED color and animation
                success = await self._led_controller.set_animation(
                    color=config.color,
                    animation=config.animation,
                    speed=config.animation_speed
                )

                if success:
                    self._current_displayed_state = config.state
                    logger.info(
                        f"LED display updated: {config.state.value} "
                        f"({config.color.to_tuple()}, {config.animation.value})"
                    )
                else:
                    logger.warning(f"Failed to update LED display for state: {config.state.value}")

        except Exception as e:
            logger.error(f"❌ Error updating LED display: {e}")

    async def _timeout_monitor_loop(self) -> None:
        """Background task to monitor and remove expired states."""
        logger.debug("LED timeout monitor started")

        try:
            while self._is_running:
                await asyncio.sleep(0.5)  # Check every 500ms

                # Check for expired states
                expired_states = []
                with self._lock:
                    for active_state in self._state_stack:
                        if active_state.is_expired():
                            expired_states.append(active_state.config.state)

                # Remove expired states
                for state in expired_states:
                    logger.debug(f"LED state expired: {state.value}")
                    await self.clear_state(state)

        except asyncio.CancelledError:
            logger.debug("LED timeout monitor cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Error in LED timeout monitor: {e}")

    def get_current_state(self) -> Optional[LEDState]:
        """
        Get currently displayed LED state.

        Returns:
            Current LED state or None if no state active
        """
        return self._current_displayed_state

    def get_state_stack(self) -> List[Dict[str, Any]]:
        """
        Get current state stack for debugging.

        Returns:
            List of active states with their info
        """
        with self._lock:
            return [
                {
                    "state": active.config.state.value,
                    "priority": active.config.priority,
                    "color": active.config.color.to_tuple(),
                    "animation": active.config.animation.value,
                    "timeout": active.config.timeout_seconds,
                    "time_remaining": active.time_remaining(),
                    "activated_at": active.activated_at.isoformat()
                }
                for active in self._state_stack
            ]

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of LED state manager.

        Returns:
            Dictionary containing status information
        """
        return {
            "initialized": self._is_running,
            "current_state": self._current_displayed_state.value if self._current_displayed_state else None,
            "active_states_count": len(self._state_stack),
            "state_stack": self.get_state_stack(),
            "hardware_status": self._led_controller.get_status()
        }

    async def set_brightness(self, brightness: float) -> bool:
        """
        Set global LED brightness.

        Args:
            brightness: Brightness level (0.0-1.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._led_controller.set_brightness(brightness)
        except Exception as e:
            logger.error(f"❌ Error setting LED brightness: {e}")
            return False
