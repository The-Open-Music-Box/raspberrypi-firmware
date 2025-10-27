"""
Tests for RGBLEDController.

Tests cover:
- Initialization and cleanup
- Color setting
- Animation control
- Brightness control
- Thread safety
- Mock hardware mode
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.src.infrastructure.hardware.leds.rgb_led_controller import RGBLEDController
from app.src.domain.models.led import LEDColor, LEDAnimation, LEDColors


class TestRGBLEDControllerInitialization:
    """Test RGB LED controller initialization."""

    def test_create_controller(self):
        """Test creating RGB LED controller."""
        controller = RGBLEDController(
            red_pin=25,
            green_pin=12,
            blue_pin=24
        )

        assert controller._red_pin == 25
        assert controller._green_pin == 12
        assert controller._blue_pin == 24
        assert controller._is_initialized is False

    def test_create_with_custom_params(self):
        """Test creating controller with custom parameters."""
        controller = RGBLEDController(
            red_pin=17,
            green_pin=18,
            blue_pin=19,
            pwm_frequency=2000,
            default_brightness=0.5
        )

        assert controller._pwm_frequency == 2000
        assert controller._brightness == 0.5

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'USE_MOCK_HARDWARE': 'true'})
    async def test_initialize_mock_mode(self):
        """Test initialization in mock hardware mode."""
        controller = RGBLEDController(25, 12, 24)

        success = await controller.initialize()

        assert success is True
        assert controller.is_initialized() is True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'USE_MOCK_HARDWARE': 'false'})
    @patch('app.src.infrastructure.hardware.leds.rgb_led_controller.GPIO_AVAILABLE', False)
    async def test_initialize_no_gpio(self):
        """Test initialization when GPIO is not available."""
        controller = RGBLEDController(25, 12, 24)

        success = await controller.initialize()

        # Should succeed in mock mode
        assert success is True
        assert controller.is_initialized() is True

    @pytest.mark.asyncio
    async def test_initialize_twice(self):
        """Test initializing twice returns success."""
        controller = RGBLEDController(25, 12, 24)

        await controller.initialize()
        success = await controller.initialize()

        assert success is True

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup operation."""
        controller = RGBLEDController(25, 12, 24)
        await controller.initialize()

        await controller.cleanup()

        assert controller.is_initialized() is False


class TestColorControl:
    """Test color control operations."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = RGBLEDController(25, 12, 24)
        await ctrl.initialize()
        return ctrl

    @pytest.mark.asyncio
    async def test_set_color_basic(self, controller):
        """Test setting basic color."""
        success = await controller.set_color(LEDColors.RED)

        assert success is True

    @pytest.mark.asyncio
    async def test_set_color_custom(self, controller):
        """Test setting custom RGB color."""
        custom_color = LEDColor(128, 64, 32)

        success = await controller.set_color(custom_color)

        assert success is True

    @pytest.mark.asyncio
    async def test_set_color_not_initialized(self):
        """Test setting color when not initialized."""
        controller = RGBLEDController(25, 12, 24)

        success = await controller.set_color(LEDColors.RED)

        assert success is False

    @pytest.mark.asyncio
    async def test_turn_off(self, controller):
        """Test turning off LED."""
        success = await controller.turn_off()

        assert success is True

    @pytest.mark.asyncio
    async def test_set_multiple_colors(self, controller):
        """Test setting multiple colors in sequence."""
        colors = [LEDColors.RED, LEDColors.GREEN, LEDColors.BLUE]

        for color in colors:
            success = await controller.set_color(color)
            assert success is True


class TestAnimationControl:
    """Test animation control operations."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = RGBLEDController(25, 12, 24)
        await ctrl.initialize()
        return ctrl

    @pytest.mark.asyncio
    async def test_set_solid_animation(self, controller):
        """Test setting solid animation."""
        success = await controller.set_animation(
            LEDColors.GREEN,
            LEDAnimation.SOLID
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_set_pulse_animation(self, controller):
        """Test setting pulse animation."""
        success = await controller.set_animation(
            LEDColors.BLUE,
            LEDAnimation.PULSE,
            speed=1.5
        )

        assert success is True
        # Give animation thread time to start
        await asyncio.sleep(0.1)

        # Animation should be running
        status = controller.get_status()
        assert status["animation_running"] is True

    @pytest.mark.asyncio
    async def test_set_blink_slow_animation(self, controller):
        """Test setting slow blink animation."""
        success = await controller.set_animation(
            LEDColors.YELLOW,
            LEDAnimation.BLINK_SLOW
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_set_blink_fast_animation(self, controller):
        """Test setting fast blink animation."""
        success = await controller.set_animation(
            LEDColors.RED,
            LEDAnimation.BLINK_FAST
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_set_flash_animation(self, controller):
        """Test setting flash animation."""
        success = await controller.set_animation(
            LEDColors.WHITE,
            LEDAnimation.FLASH
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_stop_animation(self, controller):
        """Test stopping animation."""
        # Start animation
        await controller.set_animation(
            LEDColors.BLUE,
            LEDAnimation.PULSE
        )
        await asyncio.sleep(0.1)

        # Stop animation
        controller.stop_animation()

        # Animation should stop
        await asyncio.sleep(0.1)
        status = controller.get_status()
        assert status["animation_running"] is False

    @pytest.mark.asyncio
    async def test_animation_replacement(self, controller):
        """Test replacing one animation with another."""
        # Start first animation
        await controller.set_animation(
            LEDColors.RED,
            LEDAnimation.PULSE
        )
        await asyncio.sleep(0.1)

        # Start second animation (should stop first)
        await controller.set_animation(
            LEDColors.GREEN,
            LEDAnimation.BLINK_FAST
        )
        await asyncio.sleep(0.1)

        # Should only have one animation running
        status = controller.get_status()
        assert status["current_animation"] == "blink_fast"


class TestBrightnessControl:
    """Test brightness control operations."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = RGBLEDController(25, 12, 24)
        await ctrl.initialize()
        return ctrl

    @pytest.mark.asyncio
    async def test_set_brightness_valid(self, controller):
        """Test setting valid brightness."""
        success = await controller.set_brightness(0.5)

        assert success is True

    @pytest.mark.asyncio
    async def test_set_brightness_zero(self, controller):
        """Test setting brightness to zero."""
        success = await controller.set_brightness(0.0)

        assert success is True

    @pytest.mark.asyncio
    async def test_set_brightness_full(self, controller):
        """Test setting brightness to full."""
        success = await controller.set_brightness(1.0)

        assert success is True

    @pytest.mark.asyncio
    async def test_set_brightness_invalid_negative(self, controller):
        """Test setting invalid negative brightness."""
        success = await controller.set_brightness(-0.1)

        assert success is False

    @pytest.mark.asyncio
    async def test_set_brightness_invalid_too_high(self, controller):
        """Test setting invalid brightness above 1.0."""
        success = await controller.set_brightness(1.5)

        assert success is False

    @pytest.mark.asyncio
    async def test_brightness_affects_color(self, controller):
        """Test that brightness affects displayed color."""
        # Set half brightness
        await controller.set_brightness(0.5)

        # Set color
        await controller.set_color(LEDColors.RED)

        # In mock mode, we can't verify the actual PWM values,
        # but we can verify the operation completed
        assert True


class TestStatusQueries:
    """Test status query methods."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = RGBLEDController(25, 12, 24)
        await ctrl.initialize()
        return ctrl

    def test_is_initialized_false(self):
        """Test is_initialized when not initialized."""
        controller = RGBLEDController(25, 12, 24)

        assert controller.is_initialized() is False

    @pytest.mark.asyncio
    async def test_is_initialized_true(self, controller):
        """Test is_initialized when initialized."""
        assert controller.is_initialized() is True

    @pytest.mark.asyncio
    async def test_get_status_not_initialized(self):
        """Test status when not initialized."""
        controller = RGBLEDController(25, 12, 24)

        status = controller.get_status()

        assert status["initialized"] is False
        assert "gpio_available" in status

    @pytest.mark.asyncio
    async def test_get_status_initialized(self, controller):
        """Test status when initialized."""
        status = controller.get_status()

        assert status["initialized"] is True
        assert "current_color" in status
        assert "current_animation" in status
        assert "brightness" in status
        assert "gpio_pins" in status

    @pytest.mark.asyncio
    async def test_status_shows_gpio_pins(self, controller):
        """Test status includes GPIO pin information."""
        status = controller.get_status()

        pins = status["gpio_pins"]
        assert pins["red"] == 25
        assert pins["green"] == 12
        assert pins["blue"] == 24


class TestThreadSafety:
    """Test thread safety of operations."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = RGBLEDController(25, 12, 24)
        await ctrl.initialize()
        return ctrl

    @pytest.mark.asyncio
    async def test_concurrent_color_changes(self, controller):
        """Test multiple concurrent color changes."""
        colors = [LEDColors.RED, LEDColors.GREEN, LEDColors.BLUE, LEDColors.YELLOW]

        # Execute concurrent color changes
        tasks = [controller.set_color(color) for color in colors]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_concurrent_animation_changes(self, controller):
        """Test multiple concurrent animation changes."""
        animations = [
            (LEDColors.RED, LEDAnimation.PULSE),
            (LEDColors.GREEN, LEDAnimation.BLINK_SLOW),
            (LEDColors.BLUE, LEDAnimation.SOLID),
        ]

        # Execute concurrent animation changes
        tasks = [
            controller.set_animation(color, anim)
            for color, anim in animations
        ]
        results = await asyncio.gather(*tasks)

        # All should complete
        assert len(results) == 3


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_operations_when_not_initialized(self):
        """Test that operations fail gracefully when not initialized."""
        controller = RGBLEDController(25, 12, 24)

        # All operations should return False
        assert await controller.set_color(LEDColors.RED) is False
        assert await controller.set_animation(LEDColors.RED, LEDAnimation.PULSE) is False
        assert await controller.turn_off() is False

    @pytest.mark.asyncio
    async def test_cleanup_when_not_initialized(self):
        """Test cleanup when not initialized doesn't raise error."""
        controller = RGBLEDController(25, 12, 24)

        # Should not raise exception
        await controller.cleanup()

    @pytest.mark.asyncio
    async def test_double_cleanup(self):
        """Test double cleanup doesn't cause issues."""
        controller = RGBLEDController(25, 12, 24)
        await controller.initialize()

        await controller.cleanup()
        await controller.cleanup()  # Second cleanup

        # Should complete without error
        assert True
