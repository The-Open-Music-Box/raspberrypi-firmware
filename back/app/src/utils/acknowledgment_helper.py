# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Acknowledgment Helper Utility

Centralized logic for sending WebSocket acknowledgments to clients.
This eliminates the 20+ duplications of conditional acknowledgment sending
found in nfc_api_routes.py and other API endpoints.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


async def send_ack_if_needed(
    state_manager: Optional[Any],
    client_op_id: Optional[str],
    success: bool,
    data: Optional[Any] = None,
) -> bool:
    """
    Send WebSocket acknowledgment to client if conditions are met.

    This function encapsulates the common pattern:
    ```python
    if state_manager and client_op_id:
        await state_manager.send_acknowledgment(
            client_op_id, success_flag, data_or_error
        )
    ```

    Args:
        state_manager: StateManager instance or None
        client_op_id: Client operation ID or None
        success: Whether the operation succeeded
        data: Optional data or error information to send

    Returns:
        True if acknowledgment was sent, False if conditions weren't met

    Examples:
        >>> # Success case
        >>> await send_ack_if_needed(
        ...     state_manager=state_mgr,
        ...     client_op_id="op-123",
        ...     success=True,
        ...     data={"result": "success"}
        ... )
        True

        >>> # No acknowledgment sent (missing state_manager)
        >>> await send_ack_if_needed(
        ...     state_manager=None,
        ...     client_op_id="op-123",
        ...     success=True,
        ...     data={"result": "success"}
        ... )
        False

        >>> # Error case
        >>> await send_ack_if_needed(
        ...     state_manager=state_mgr,
        ...     client_op_id="op-123",
        ...     success=False,
        ...     data={"message": "Operation failed"}
        ... )
        True
    """
    # Check if both conditions are met
    if not state_manager or not client_op_id:
        # Log only if one is present but not both (might indicate misconfiguration)
        if state_manager and not client_op_id:
            logger.debug("State manager present but no client_op_id - skipping acknowledgment")
        elif client_op_id and not state_manager:
            logger.warning(
                f"Client operation ID present ({client_op_id}) but no state manager - "
                "acknowledgment cannot be sent"
            )
        return False

    try:
        # Send the acknowledgment
        await state_manager.send_acknowledgment(client_op_id, success, data)
        logger.debug(
            f"Sent acknowledgment for operation {client_op_id}: "
            f"success={success}, has_data={data is not None}"
        )
        return True
    except Exception as e:
        # Log but don't raise - acknowledgment failures shouldn't break the main operation
        logger.error(
            f"Failed to send acknowledgment for operation {client_op_id}: {str(e)}",
            exc_info=True
        )
        return False


async def send_success_ack(
    state_manager: Optional[Any],
    client_op_id: Optional[str],
    data: Optional[Any] = None,
) -> bool:
    """
    Convenience function to send a success acknowledgment.

    Args:
        state_manager: StateManager instance or None
        client_op_id: Client operation ID or None
        data: Optional success data to send

    Returns:
        True if acknowledgment was sent, False otherwise

    Examples:
        >>> await send_success_ack(
        ...     state_manager=state_mgr,
        ...     client_op_id="op-123",
        ...     data={"association": association_data}
        ... )
        True
    """
    return await send_ack_if_needed(state_manager, client_op_id, True, data)


async def send_error_ack(
    state_manager: Optional[Any],
    client_op_id: Optional[str],
    error_message: str,
    error_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Convenience function to send an error acknowledgment.

    Args:
        state_manager: StateManager instance or None
        client_op_id: Client operation ID or None
        error_message: Error message to send
        error_data: Optional additional error data

    Returns:
        True if acknowledgment was sent, False otherwise

    Examples:
        >>> await send_error_ack(
        ...     state_manager=state_mgr,
        ...     client_op_id="op-123",
        ...     error_message="Failed to associate tag",
        ...     error_data={"reason": "tag_not_found"}
        ... )
        True
    """
    error_payload = error_data or {}
    error_payload["message"] = error_message

    return await send_ack_if_needed(state_manager, client_op_id, False, error_payload)


class AcknowledgmentContext:
    """
    Context manager for automatic acknowledgment sending.

    This allows using a with-statement to ensure acknowledgments are sent
    even if exceptions occur.

    Examples:
        >>> async with AcknowledgmentContext(
        ...     state_manager=state_mgr,
        ...     client_op_id="op-123"
        ... ) as ack:
        ...     # Perform operation
        ...     result = await some_operation()
        ...     # Mark as successful with data
        ...     ack.set_success(result)
        ... # Acknowledgment sent automatically on exit
    """

    def __init__(
        self,
        state_manager: Optional[Any],
        client_op_id: Optional[str],
    ):
        """
        Initialize acknowledgment context.

        Args:
            state_manager: StateManager instance or None
            client_op_id: Client operation ID or None
        """
        self.state_manager = state_manager
        self.client_op_id = client_op_id
        self.success = False
        self.data = None
        self._completed = False

    def set_success(self, data: Optional[Any] = None):
        """
        Mark operation as successful and set data.

        Args:
            data: Optional success data
        """
        self.success = True
        self.data = data
        self._completed = True

    def set_error(self, error_message: str, error_data: Optional[Dict[str, Any]] = None):
        """
        Mark operation as failed and set error data.

        Args:
            error_message: Error message
            error_data: Optional additional error data
        """
        self.success = False
        error_payload = error_data or {}
        error_payload["message"] = error_message
        self.data = error_payload
        self._completed = True

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exit async context and send acknowledgment.

        If an exception occurred and success wasn't explicitly set,
        automatically send an error acknowledgment.
        """
        if exc_type is not None and not self._completed:
            # Exception occurred and no explicit status was set
            self.set_error(
                error_message=f"Operation failed: {str(exc_val)}",
                error_data={"exception_type": exc_type.__name__}
            )

        # Send acknowledgment
        await send_ack_if_needed(
            self.state_manager,
            self.client_op_id,
            self.success,
            self.data
        )

        # Don't suppress exceptions
        return False
