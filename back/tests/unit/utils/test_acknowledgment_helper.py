# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for acknowledgment_helper utility.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from app.src.utils.acknowledgment_helper import (
    send_ack_if_needed,
    send_success_ack,
    send_error_ack,
    AcknowledgmentContext,
)


class TestSendAckIfNeeded:
    """Test suite for send_ack_if_needed function."""

    @pytest.mark.asyncio
    async def test_sends_acknowledgment_when_conditions_met(self):
        """Test that acknowledgment is sent when state_manager and client_op_id are present."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        success = True
        data = {"result": "success"}

        # Act
        result = await send_ack_if_needed(state_manager, client_op_id, success, data)

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            client_op_id, success, data
        )

    @pytest.mark.asyncio
    async def test_no_acknowledgment_when_state_manager_missing(self):
        """Test that no acknowledgment is sent when state_manager is None."""
        # Arrange
        state_manager = None
        client_op_id = "op-123"

        # Act
        result = await send_ack_if_needed(state_manager, client_op_id, True, {})

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_no_acknowledgment_when_client_op_id_missing(self):
        """Test that no acknowledgment is sent when client_op_id is None."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = None

        # Act
        result = await send_ack_if_needed(state_manager, client_op_id, True, {})

        # Assert
        assert result is False
        state_manager.send_acknowledgment.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_acknowledgment_when_both_missing(self):
        """Test that no acknowledgment is sent when both parameters are None."""
        # Act
        result = await send_ack_if_needed(None, None, True, {})

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_sends_success_acknowledgment(self):
        """Test sending success acknowledgment."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        data = {"association": "data"}

        # Act
        result = await send_ack_if_needed(state_manager, client_op_id, True, data)

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            client_op_id, True, data
        )

    @pytest.mark.asyncio
    async def test_sends_error_acknowledgment(self):
        """Test sending error acknowledgment."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        error_data = {"message": "Operation failed"}

        # Act
        result = await send_ack_if_needed(state_manager, client_op_id, False, error_data)

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            client_op_id, False, error_data
        )

    @pytest.mark.asyncio
    async def test_handles_acknowledgment_failure_gracefully(self):
        """Test that acknowledgment failures are handled gracefully."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        client_op_id = "op-123"

        # Act - should not raise exception
        result = await send_ack_if_needed(state_manager, client_op_id, True, {})

        # Assert
        assert result is False
        state_manager.send_acknowledgment.assert_called_once()


class TestSendSuccessAck:
    """Test suite for send_success_ack convenience function."""

    @pytest.mark.asyncio
    async def test_sends_success_acknowledgment(self):
        """Test that success acknowledgment is sent correctly."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        data = {"result": "ok"}

        # Act
        result = await send_success_ack(state_manager, client_op_id, data)

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            client_op_id, True, data
        )

    @pytest.mark.asyncio
    async def test_sends_success_without_data(self):
        """Test sending success acknowledgment without data."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"

        # Act
        result = await send_success_ack(state_manager, client_op_id)

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            client_op_id, True, None
        )


class TestSendErrorAck:
    """Test suite for send_error_ack convenience function."""

    @pytest.mark.asyncio
    async def test_sends_error_acknowledgment_with_message(self):
        """Test that error acknowledgment is sent with message."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        error_message = "Operation failed"

        # Act
        result = await send_error_ack(state_manager, client_op_id, error_message)

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        assert call_args[0][0] == client_op_id
        assert call_args[0][1] is False
        assert call_args[0][2]["message"] == error_message

    @pytest.mark.asyncio
    async def test_sends_error_acknowledgment_with_data(self):
        """Test that error acknowledgment includes additional error data."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        error_message = "Validation failed"
        error_data = {"field": "tag_id", "reason": "invalid_format"}

        # Act
        result = await send_error_ack(
            state_manager, client_op_id, error_message, error_data
        )

        # Assert
        assert result is True
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        error_payload = call_args[0][2]
        assert error_payload["message"] == error_message
        assert error_payload["field"] == "tag_id"
        assert error_payload["reason"] == "invalid_format"


class TestAcknowledgmentContext:
    """Test suite for AcknowledgmentContext context manager."""

    @pytest.mark.asyncio
    async def test_sends_acknowledgment_on_success(self):
        """Test that success acknowledgment is sent when set_success is called."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        success_data = {"result": "completed"}

        # Act
        async with AcknowledgmentContext(state_manager, client_op_id) as ack:
            ack.set_success(success_data)

        # Assert
        state_manager.send_acknowledgment.assert_called_once_with(
            client_op_id, True, success_data
        )

    @pytest.mark.asyncio
    async def test_sends_acknowledgment_on_error(self):
        """Test that error acknowledgment is sent when set_error is called."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"
        error_message = "Operation failed"

        # Act
        async with AcknowledgmentContext(state_manager, client_op_id) as ack:
            ack.set_error(error_message)

        # Assert
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        assert call_args[0][0] == client_op_id
        assert call_args[0][1] is False
        assert call_args[0][2]["message"] == error_message

    @pytest.mark.asyncio
    async def test_automatically_sends_error_on_exception(self):
        """Test that error acknowledgment is automatically sent on exception."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"

        # Act & Assert
        with pytest.raises(ValueError):
            async with AcknowledgmentContext(state_manager, client_op_id) as ack:
                raise ValueError("Test exception")

        # Verify error acknowledgment was sent
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        assert call_args[0][1] is False  # success=False
        assert "Test exception" in call_args[0][2]["message"]
        assert call_args[0][2]["exception_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_does_not_suppress_exceptions(self):
        """Test that exceptions are not suppressed by context manager."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"

        # Act & Assert
        with pytest.raises(RuntimeError):
            async with AcknowledgmentContext(state_manager, client_op_id):
                raise RuntimeError("Test error")

    @pytest.mark.asyncio
    async def test_no_acknowledgment_when_state_manager_missing(self):
        """Test that context manager handles missing state_manager gracefully."""
        # Act - should not raise exception
        async with AcknowledgmentContext(None, "op-123") as ack:
            ack.set_success({"result": "ok"})

        # No assertion needed - just verify no exception was raised

    @pytest.mark.asyncio
    async def test_explicit_status_takes_precedence_over_exception(self):
        """Test that explicitly set status is used even if exception occurs."""
        # Arrange
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock()
        client_op_id = "op-123"

        # Act
        try:
            async with AcknowledgmentContext(state_manager, client_op_id) as ack:
                ack.set_success({"result": "partial"})
                raise ValueError("Later exception")
        except ValueError:
            pass

        # Assert - should have sent success, not error
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        assert call_args[0][1] is True  # success=True
        assert call_args[0][2] == {"result": "partial"}
