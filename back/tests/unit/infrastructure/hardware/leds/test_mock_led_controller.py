"""
Tests for MockLEDController.

Tests cover:
- Basic operations
- Operation tracking
- Test helper methods
"""

import pytest

from app.src.infrastructure.hardware.leds.mock_led_controller import MockLEDController
from app.src.domain.models.led import LEDColor, LEDAnimation, LEDColors


class TestMockLEDControllerBasics:
    """Test basic MockLEDController operations."""

    def test_create_mock_controller(self):
        """Test creating mock LED controller."""
        controller = MockLEDController()

        assert controller.is_initialized() is False
        assert len(controller.get_operations()) == 0

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialization."""
        controller = MockLEDController()

        success = await controller.initialize()

        assert success is True
        assert controller.is_initialized() is True

        ops = controller.get_operations()
        assert len(ops) == 1
        assert ops[0][0] == "initialize"

    @pytest.mark.asyncio
    async def test_initialize_twice(self):
        """Test initializing twice."""
        controller = MockLEDController()

        await controller.initialize()
        success = await controller.initialize()

        assert success is True
        # Should log warning but still succeed

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup."""
        controller = MockLEDController()
        await controller.initialize()

        await controller.cleanup()

        assert controller.is_initialized() is False
        assert controller.get_current_color() == LEDColors.OFF


class TestColorOperations:
    """Test color control operations."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = MockLEDController()
        await ctrl.initialize()
        ctrl.clear_operations()  # Clear initialization operation
        return ctrl

    @pytest.mark.asyncio
    async def test_set_color(self, controller):
        """Test setting color."""
        success = await controller.set_color(LEDColors.RED)

        assert success is True
        assert controller.get_current_color() == LEDColors.RED
        assert controller.get_current_animation() == LEDAnimation.SOLID

        ops = controller.get_operations()
        assert len(ops) == 1
        assert ops[0][0] == "set_color"
        assert ops[0][1]["color"] == (255, 0, 0)

    @pytest.mark.asyncio
    async def test_set_multiple_colors(self, controller):
        """Test setting multiple colors."""
        colors = [LEDColors.RED, LEDColors.GREEN, LEDColors.BLUE]

        for color in colors:
            await controller.set_color(color)

        assert controller.get_current_color() == LEDColors.BLUE
        assert len(controller.get_operations()) == 3

    @pytest.mark.asyncio
    async def test_turn_off(self, controller):
        """Test turning off LED."""
        await controller.set_color(LEDColors.RED)
        controller.clear_operations()

        success = await controller.turn_off()

        assert success is True
        assert controller.get_current_color() == LEDColors.OFF

    @pytest.mark.asyncio
    async def test_set_color_not_initialized(self):
        """Test setting color when not initialized."""
        controller = MockLEDController()

        success = await controller.set_color(LEDColors.RED)

        assert success is False


class TestAnimationOperations:
    """Test animation control operations."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = MockLEDController()
        await ctrl.initialize()
        ctrl.clear_operations()
        return ctrl

    @pytest.mark.asyncio
    async def test_set_animation_solid(self, controller):
        """Test setting solid animation."""
        success = await controller.set_animation(
            LEDColors.GREEN,
            LEDAnimation.SOLID
        )

        assert success is True
        assert controller.get_current_color() == LEDColors.GREEN
        assert controller.get_current_animation() == LEDAnimation.SOLID

    @pytest.mark.asyncio
    async def test_set_animation_pulse(self, controller):
        """Test setting pulse animation."""
        success = await controller.set_animation(
            LEDColors.BLUE,
            LEDAnimation.PULSE,
            speed=1.5
        )

        assert success is True
        assert controller.get_current_animation() == LEDAnimation.PULSE

        ops = controller.get_operations()
        assert len(ops) == 1
        assert ops[0][0] == "set_animation"
        assert ops[0][1]["color"] == (0, 0, 255)
        assert ops[0][1]["animation"] == "pulse"
        assert ops[0][1]["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_set_animation_blink(self, controller):
        """Test setting blink animation."""
        await controller.set_animation(
            LEDColors.YELLOW,
            LEDAnimation.BLINK_SLOW
        )

        assert controller.get_current_animation() == LEDAnimation.BLINK_SLOW

    @pytest.mark.asyncio
    async def test_stop_animation(self, controller):
        """Test stopping animation."""
        controller.stop_animation()

        ops = controller.get_operations()
        assert len(ops) == 1
        assert ops[0][0] == "stop_animation"

    @pytest.mark.asyncio
    async def test_set_animation_not_initialized(self):
        """Test setting animation when not initialized."""
        controller = MockLEDController()

        success = await controller.set_animation(
            LEDColors.RED,
            LEDAnimation.PULSE
        )

        assert success is False


class TestBrightnessControl:
    """Test brightness control."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = MockLEDController()
        await ctrl.initialize()
        ctrl.clear_operations()
        return ctrl

    @pytest.mark.asyncio
    async def test_set_brightness_valid(self, controller):
        """Test setting valid brightness."""
        success = await controller.set_brightness(0.5)

        assert success is True
        assert controller.get_brightness() == 0.5

        ops = controller.get_operations()
        assert len(ops) == 1
        assert ops[0][0] == "set_brightness"
        assert ops[0][1]["brightness"] == 0.5

    @pytest.mark.asyncio
    async def test_set_brightness_zero(self, controller):
        """Test setting brightness to zero."""
        success = await controller.set_brightness(0.0)

        assert success is True
        assert controller.get_brightness() == 0.0

    @pytest.mark.asyncio
    async def test_set_brightness_full(self, controller):
        """Test setting brightness to full."""
        success = await controller.set_brightness(1.0)

        assert success is True
        assert controller.get_brightness() == 1.0

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


class TestOperationTracking:
    """Test operation tracking for tests."""

    @pytest.mark.asyncio
    async def test_track_all_operations(self):
        """Test that all operations are tracked."""
        controller = MockLEDController()

        await controller.initialize()
        await controller.set_color(LEDColors.RED)
        await controller.set_animation(LEDColors.BLUE, LEDAnimation.PULSE)
        await controller.set_brightness(0.5)
        controller.stop_animation()
        await controller.cleanup()

        ops = controller.get_operations()
        assert len(ops) == 6
        assert ops[0][0] == "initialize"
        assert ops[1][0] == "set_color"
        assert ops[2][0] == "set_animation"
        assert ops[3][0] == "set_brightness"
        assert ops[4][0] == "stop_animation"
        assert ops[5][0] == "cleanup"

    @pytest.mark.asyncio
    async def test_clear_operations(self):
        """Test clearing operation history."""
        controller = MockLEDController()

        await controller.initialize()
        await controller.set_color(LEDColors.RED)

        assert len(controller.get_operations()) == 2

        controller.clear_operations()

        assert len(controller.get_operations()) == 0

    @pytest.mark.asyncio
    async def test_operations_immutable_copy(self):
        """Test that get_operations returns a copy."""
        controller = MockLEDController()
        await controller.initialize()

        ops1 = controller.get_operations()
        ops1.append(("fake", {}))

        ops2 = controller.get_operations()

        # Original should not be affected
        assert len(ops2) == 1


class TestStatusQueries:
    """Test status query methods."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = MockLEDController()
        await ctrl.initialize()
        return ctrl

    def test_is_initialized_false(self):
        """Test is_initialized when not initialized."""
        controller = MockLEDController()

        assert controller.is_initialized() is False

    @pytest.mark.asyncio
    async def test_is_initialized_true(self, controller):
        """Test is_initialized when initialized."""
        assert controller.is_initialized() is True

    @pytest.mark.asyncio
    async def test_get_status(self, controller):
        """Test getting status."""
        await controller.set_color(LEDColors.GREEN)
        await controller.set_brightness(0.7)

        status = controller.get_status()

        assert status["initialized"] is True
        assert status["mock_mode"] is True
        assert status["gpio_available"] is False
        assert status["current_color"] == (0, 255, 0)
        assert status["current_animation"] == "solid"
        assert status["brightness"] == 0.7
        assert status["operations_count"] >= 2

    @pytest.mark.asyncio
    async def test_get_status_after_animation(self, controller):
        """Test status includes animation information."""
        await controller.set_animation(
            LEDColors.BLUE,
            LEDAnimation.PULSE,
            speed=2.0
        )

        status = controller.get_status()

        assert status["current_animation"] == "pulse"
        assert status["animation_speed"] == 2.0


class TestTestHelpers:
    """Test helper methods for testing."""

    @pytest.fixture
    async def controller(self):
        """Create initialized controller."""
        ctrl = MockLEDController()
        await ctrl.initialize()
        ctrl.clear_operations()
        return ctrl

    @pytest.mark.asyncio
    async def test_get_current_color(self, controller):
        """Test getting current color."""
        await controller.set_color(LEDColors.MAGENTA)

        color = controller.get_current_color()

        assert color == LEDColors.MAGENTA
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 255

    @pytest.mark.asyncio
    async def test_get_current_animation(self, controller):
        """Test getting current animation."""
        await controller.set_animation(
            LEDColors.RED,
            LEDAnimation.BLINK_FAST
        )

        animation = controller.get_current_animation()

        assert animation == LEDAnimation.BLINK_FAST

    @pytest.mark.asyncio
    async def test_get_brightness(self, controller):
        """Test getting brightness."""
        await controller.set_brightness(0.3)

        brightness = controller.get_brightness()

        assert brightness == 0.3
