# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Button Action Dispatcher (Application Layer).

Dispatches button press events to configured actions.
This is the Invoker in the Command Pattern.
"""

import asyncio
from typing import Dict, List, Optional
import logging

from app.src.domain.actions.button_actions import (
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
from app.src.domain.protocols.playback_coordinator_protocol import PlaybackCoordinatorProtocol
from app.src.config.button_actions_config import ButtonActionConfig

logger = logging.getLogger(__name__)


class ButtonActionDispatcher:
    """
    Dispatches button events to configured actions.

    This class:
    1. Maintains a registry of available actions
    2. Maps button IDs to their configured actions based on ButtonActionConfig
    3. Executes actions when buttons are pressed
    """

    def __init__(self, configs: List[ButtonActionConfig], coordinator: PlaybackCoordinatorProtocol):
        """
        Initialize the button action dispatcher.

        Args:
            configs: List of button configurations
            coordinator: PlaybackCoordinator to execute actions on
        """
        self._coordinator = coordinator
        self._configs = configs

        # Build action registry (action_name -> Action instance)
        self._action_registry = self._build_action_registry()

        # Map button IDs to actions based on config
        self._button_to_action = self._map_buttons_to_actions(configs)

        logger.info(
            f"ButtonActionDispatcher initialized with {len(self._button_to_action)} "
            f"button mappings from {len(self._action_registry)} available actions"
        )

    def _build_action_registry(self) -> Dict[str, ButtonAction]:
        """
        Build registry of all available actions.

        Returns:
            Dictionary mapping action names to action instances
        """
        actions = [
            PlayAction(),
            PauseAction(),
            PlayPauseAction(),
            StopAction(),
            NextTrackAction(),
            PreviousTrackAction(),
            VolumeUpAction(),
            VolumeDownAction(),
            PrintDebugAction(),
        ]

        registry = {action.name: action for action in actions}
        logger.debug(f"Action registry built with {len(registry)} actions: {list(registry.keys())}")
        return registry

    def _map_buttons_to_actions(self, configs: List[ButtonActionConfig]) -> Dict[int, ButtonAction]:
        """
        Map button IDs to their configured actions.

        Args:
            configs: List of button configurations

        Returns:
            Dictionary mapping button IDs to ButtonAction instances
        """
        button_map = {}

        for config in configs:
            if not config.enabled:
                logger.debug(f"Skipping disabled button {config.button_id}")
                continue

            action = self._action_registry.get(config.action_name)
            if action:
                button_map[config.button_id] = action
                logger.info(
                    f"✅ Button {config.button_id} (GPIO {config.gpio_pin}) "
                    f"mapped to action '{action.name}'"
                )
            else:
                logger.warning(
                    f"⚠️ Unknown action '{config.action_name}' for button {config.button_id}, "
                    f"button will be ignored"
                )

        return button_map

    async def dispatch(self, button_id: int) -> bool:
        """
        Dispatch a button press event to its configured action.

        Args:
            button_id: ID of the button that was pressed

        Returns:
            True if action executed successfully, False otherwise
        """
        action = self._button_to_action.get(button_id)

        if not action:
            logger.warning(f"⚠️ No action configured for button {button_id}")
            return False

        try:
            logger.info(f"🔘 Button {button_id} pressed, dispatching to action '{action.name}'")
            success = await action.execute(self._coordinator)

            if success:
                logger.debug(f"✅ Action '{action.name}' completed successfully")
            else:
                logger.warning(f"⚠️ Action '{action.name}' failed")

            return success

        except Exception as e:
            logger.error(f"❌ Error executing action '{action.name}' for button {button_id}: {e}")
            return False

    def dispatch_sync(self, button_id: int) -> bool:
        """
        Synchronous wrapper for dispatch (for use from GPIO callbacks).

        Args:
            button_id: ID of the button that was pressed

        Returns:
            True if action dispatched successfully, False otherwise
        """
        try:
            # Create new event loop or use existing one
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, schedule as a task
                asyncio.create_task(self.dispatch(button_id))
                return True
            else:
                # Run in the event loop
                return loop.run_until_complete(self.dispatch(button_id))
        except Exception as e:
            logger.error(f"❌ Error in sync dispatch for button {button_id}: {e}")
            return False

    def get_button_action(self, button_id: int) -> Optional[ButtonAction]:
        """
        Get the action configured for a specific button.

        Args:
            button_id: Button ID to look up

        Returns:
            ButtonAction if configured, None otherwise
        """
        return self._button_to_action.get(button_id)

    def get_configured_buttons(self) -> List[int]:
        """
        Get list of configured button IDs.

        Returns:
            List of button IDs that have actions configured
        """
        return list(self._button_to_action.keys())

    def get_status(self) -> Dict[str, any]:
        """
        Get dispatcher status information.

        Returns:
            Dictionary containing status information
        """
        return {
            "total_actions": len(self._action_registry),
            "configured_buttons": len(self._button_to_action),
            "available_actions": list(self._action_registry.keys()),
            "button_mappings": {
                button_id: action.name
                for button_id, action in self._button_to_action.items()
            }
        }
