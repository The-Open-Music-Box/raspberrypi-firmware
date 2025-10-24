# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for button actions configuration."""

import pytest
from app.src.config.button_actions_config import (
    ButtonActionConfig,
    DEFAULT_BUTTON_CONFIGS,
    AVAILABLE_ACTIONS,
    validate_button_configs,
    get_button_config_by_id,
    get_button_config_by_pin,
)


class TestButtonActionConfig:
    """Tests for ButtonActionConfig dataclass."""

    def test_valid_config_creation(self):
        """Test creating a valid button configuration."""
        config = ButtonActionConfig(
            button_id=0,
            gpio_pin=23,
            action_name="play_pause",
            enabled=True,
            description="Toggle play/pause"
        )

        assert config.button_id == 0
        assert config.gpio_pin == 23
        assert config.action_name == "play_pause"
        assert config.enabled is True
        assert config.description == "Toggle play/pause"

    def test_config_with_defaults(self):
        """Test creating config with default values."""
        config = ButtonActionConfig(
            button_id=1,
            gpio_pin=20,
            action_name="next_track"
        )

        assert config.enabled is True  # Default
        assert config.description is None  # Default

    def test_invalid_button_id_too_low(self):
        """Test that button_id < 0 raises ValueError."""
        with pytest.raises(ValueError, match="button_id must be between 0 and 4"):
            ButtonActionConfig(
                button_id=-1,
                gpio_pin=23,
                action_name="play"
            )

    def test_invalid_button_id_too_high(self):
        """Test that button_id > 4 raises ValueError."""
        with pytest.raises(ValueError, match="button_id must be between 0 and 4"):
            ButtonActionConfig(
                button_id=5,
                gpio_pin=23,
                action_name="play"
            )

    def test_invalid_gpio_pin_too_low(self):
        """Test that gpio_pin < 0 raises ValueError."""
        with pytest.raises(ValueError, match="gpio_pin must be between 0 and 27"):
            ButtonActionConfig(
                button_id=0,
                gpio_pin=-1,
                action_name="play"
            )

    def test_invalid_gpio_pin_too_high(self):
        """Test that gpio_pin > 27 raises ValueError."""
        with pytest.raises(ValueError, match="gpio_pin must be between 0 and 27"):
            ButtonActionConfig(
                button_id=0,
                gpio_pin=28,
                action_name="play"
            )

    def test_empty_action_name(self):
        """Test that empty action_name raises ValueError."""
        with pytest.raises(ValueError, match="action_name cannot be empty"):
            ButtonActionConfig(
                button_id=0,
                gpio_pin=23,
                action_name=""
            )


class TestDefaultButtonConfigs:
    """Tests for DEFAULT_BUTTON_CONFIGS constant."""

    def test_default_configs_exist(self):
        """Test that default configs are defined."""
        assert len(DEFAULT_BUTTON_CONFIGS) == 5

    def test_default_configs_have_correct_buttons(self):
        """Test that all buttons 0-4 are configured."""
        button_ids = {config.button_id for config in DEFAULT_BUTTON_CONFIGS}
        assert button_ids == {0, 1, 2, 3, 4}

    def test_default_configs_gpio_assignments(self):
        """Test that default configs have correct GPIO assignments."""
        expected_pins = {0: 23, 1: 20, 2: 16, 3: 26, 4: 19}

        for config in DEFAULT_BUTTON_CONFIGS:
            assert config.gpio_pin == expected_pins[config.button_id]

    def test_default_configs_actions(self):
        """Test that default configs have correct actions."""
        expected_actions = {
            0: "print_debug",
            1: "volume_down",
            2: "previous_track",
            3: "next_track",
            4: "volume_up",
        }

        for config in DEFAULT_BUTTON_CONFIGS:
            assert config.action_name == expected_actions[config.button_id]

    def test_default_configs_all_enabled(self):
        """Test that all default configs are enabled."""
        for config in DEFAULT_BUTTON_CONFIGS:
            assert config.enabled is True


class TestAvailableActions:
    """Tests for AVAILABLE_ACTIONS constant."""

    def test_available_actions_defined(self):
        """Test that available actions are defined."""
        assert len(AVAILABLE_ACTIONS) > 0

    def test_required_actions_present(self):
        """Test that all required actions are in AVAILABLE_ACTIONS."""
        required_actions = {
            "play",
            "pause",
            "play_pause",
            "next_track",
            "previous_track",
            "volume_up",
            "volume_down",
            "stop",
            "print_debug",
        }

        assert required_actions.issubset(AVAILABLE_ACTIONS)


class TestValidateButtonConfigs:
    """Tests for validate_button_configs function."""

    def test_valid_configs(self):
        """Test validation of valid configs."""
        configs = [
            ButtonActionConfig(0, 23, "play_pause"),
            ButtonActionConfig(1, 20, "next_track"),
        ]

        errors = validate_button_configs(configs)
        assert errors == []

    def test_duplicate_button_ids(self):
        """Test validation detects duplicate button IDs."""
        configs = [
            ButtonActionConfig(0, 23, "play_pause"),
            ButtonActionConfig(0, 20, "next_track"),  # Duplicate ID
        ]

        errors = validate_button_configs(configs)
        assert len(errors) == 1
        assert "Duplicate button IDs" in errors[0]

    def test_duplicate_gpio_pins(self):
        """Test validation detects duplicate GPIO pins."""
        configs = [
            ButtonActionConfig(0, 23, "play_pause"),
            ButtonActionConfig(1, 23, "next_track"),  # Duplicate pin
        ]

        errors = validate_button_configs(configs)
        assert len(errors) == 1
        assert "Duplicate GPIO pin" in errors[0]

    def test_disabled_button_allows_duplicate_pin(self):
        """Test that disabled buttons don't count for pin duplication."""
        configs = [
            ButtonActionConfig(0, 23, "play_pause", enabled=True),
            ButtonActionConfig(1, 23, "next_track", enabled=False),  # Disabled, same pin OK
        ]

        errors = validate_button_configs(configs)
        assert errors == []

    def test_unknown_action(self):
        """Test validation detects unknown actions."""
        configs = [
            ButtonActionConfig(0, 23, "unknown_action"),
        ]

        errors = validate_button_configs(configs)
        assert len(errors) == 1
        assert "Unknown action" in errors[0]
        assert "unknown_action" in errors[0]

    def test_multiple_errors(self):
        """Test validation detects multiple errors."""
        configs = [
            ButtonActionConfig(0, 23, "unknown_action"),
            ButtonActionConfig(0, 20, "play_pause"),  # Duplicate ID
        ]

        errors = validate_button_configs(configs)
        assert len(errors) == 2


class TestGetButtonConfigById:
    """Tests for get_button_config_by_id function."""

    def test_find_existing_button(self):
        """Test finding an existing button by ID."""
        config = get_button_config_by_id(0)

        assert config is not None
        assert config.button_id == 0
        assert config.action_name == "print_debug"

    def test_find_nonexistent_button(self):
        """Test finding a nonexistent button returns None."""
        config = get_button_config_by_id(99)
        assert config is None

    def test_find_disabled_button(self):
        """Test finding a disabled button returns None."""
        configs = [
            ButtonActionConfig(0, 23, "play", enabled=False),
        ]

        config = get_button_config_by_id(0, configs)
        assert config is None

    def test_custom_configs(self):
        """Test with custom configs list."""
        custom_configs = [
            ButtonActionConfig(0, 23, "stop"),
            ButtonActionConfig(1, 20, "pause"),
        ]

        config = get_button_config_by_id(0, custom_configs)
        assert config is not None
        assert config.action_name == "stop"


class TestGetButtonConfigByPin:
    """Tests for get_button_config_by_pin function."""

    def test_find_existing_pin(self):
        """Test finding an existing button by GPIO pin."""
        config = get_button_config_by_pin(23)

        assert config is not None
        assert config.gpio_pin == 23
        assert config.button_id == 0

    def test_find_nonexistent_pin(self):
        """Test finding a nonexistent GPIO pin returns None."""
        config = get_button_config_by_pin(99)
        assert config is None

    def test_find_disabled_button_pin(self):
        """Test finding a disabled button by pin returns None."""
        configs = [
            ButtonActionConfig(0, 23, "play", enabled=False),
        ]

        config = get_button_config_by_pin(23, configs)
        assert config is None

    def test_custom_configs(self):
        """Test with custom configs list."""
        custom_configs = [
            ButtonActionConfig(0, 10, "stop"),
            ButtonActionConfig(1, 11, "pause"),
        ]

        config = get_button_config_by_pin(10, custom_configs)
        assert config is not None
        assert config.action_name == "stop"
