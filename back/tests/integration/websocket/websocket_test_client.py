# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
WebSocket Test Client for TheOpenMusicBox integration tests.

This module provides a reusable Socket.IO client for testing real-time
functionality, contract compliance, and multi-client synchronization.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

import socketio

logger = logging.getLogger(__name__)


@dataclass
class CapturedEvent:
    """Represents a captured Socket.IO event with metadata."""

    event_type: str
    data: Dict[str, Any]
    timestamp: float
    client_id: str

    def __repr__(self) -> str:
        return f"CapturedEvent(event_type={self.event_type}, timestamp={self.timestamp})"


class WebSocketTestClient:
    """
    A Socket.IO test client for TheOpenMusicBox integration tests.

    Features:
    - Async connection management
    - Event capturing with timestamps
    - Room subscription (join:playlists, join:playlist, etc.)
    - Event filtering and waiting
    - Contract validation integration
    - Multi-client support

    Example usage:
        client = WebSocketTestClient("http://localhost:8000", client_id="test-client-1")
        await client.connect()
        await client.join_room("playlists")

        # Trigger some action...

        event = await client.wait_for_event("state:playlists", timeout=5.0)
        assert event.data["server_seq"] > 0

        await client.disconnect()
    """

    def __init__(
        self,
        base_url: str,
        client_id: Optional[str] = None,
        contract_validator: Optional[Any] = None,
        auto_validate: bool = True,
        capture_all_events: bool = True
    ):
        """
        Initialize WebSocket test client.

        Args:
            base_url: Base URL of the backend (e.g., "http://localhost:8000")
            client_id: Unique identifier for this client (for debugging)
            contract_validator: ContractValidator instance for automatic validation
            auto_validate: Automatically validate events against contracts
            capture_all_events: Capture all events (True) or only explicitly requested
        """
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id or f"test-client-{id(self)}"
        self.contract_validator = contract_validator
        self.auto_validate = auto_validate and contract_validator is not None
        self.capture_all_events = capture_all_events

        # Socket.IO client
        self.sio = socketio.AsyncClient(
            logger=logger,
            engineio_logger=logger
        )

        # Event storage
        self.captured_events: List[CapturedEvent] = []
        self._event_callbacks: Dict[str, List[Callable]] = {}
        self._connection_ready = asyncio.Event()
        self._is_connected = False

        # Connection metadata
        self.sid: Optional[str] = None
        self.server_seq_on_connect: Optional[int] = None

        # Setup default event handlers
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Setup default Socket.IO event handlers."""

        @self.sio.event
        async def connect():
            """Handle successful connection."""
            logger.info(f"[{self.client_id}] Connected to server")
            self._is_connected = True
            self._connection_ready.set()

        @self.sio.event
        async def disconnect():
            """Handle disconnection."""
            logger.info(f"[{self.client_id}] Disconnected from server")
            self._is_connected = False
            self._connection_ready.clear()

        @self.sio.event
        async def connection_status(data):
            """Handle connection_status event from server."""
            logger.info(f"[{self.client_id}] Connection status: {data}")
            self.sid = data.get('sid')
            self.server_seq_on_connect = data.get('server_seq')
            await self._handle_event('connection_status', data)

        @self.sio.on('*')
        async def catch_all(event, data):
            """Catch-all handler for events."""
            if self.capture_all_events:
                await self._handle_event(event, data)

    async def _handle_event(self, event_type: str, data: Any):
        """
        Internal handler for captured events.

        Args:
            event_type: Type of the event
            data: Event payload
        """
        # Create captured event
        captured = CapturedEvent(
            event_type=event_type,
            data=data if isinstance(data, dict) else {"payload": data},
            timestamp=datetime.now().timestamp(),
            client_id=self.client_id
        )

        # Store event
        self.captured_events.append(captured)

        # Log event
        logger.debug(
            f"[{self.client_id}] Event captured: {event_type} "
            f"(total: {len(self.captured_events)})"
        )

        # Auto-validate against contracts if enabled
        if self.auto_validate and event_type.startswith('state:'):
            try:
                self.contract_validator.validate_event(event_type, data)
                logger.debug(f"[{self.client_id}] Contract validation passed for {event_type}")
            except Exception as e:
                logger.error(
                    f"[{self.client_id}] Contract validation failed for {event_type}: {e}"
                )
                # Don't raise, just log - allows tests to explicitly check

        # Trigger custom callbacks
        if event_type in self._event_callbacks:
            for callback in self._event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(captured)
                    else:
                        callback(captured)
                except Exception as e:
                    logger.error(
                        f"[{self.client_id}] Error in callback for {event_type}: {e}"
                    )

    async def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to the Socket.IO server.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connection successful, False otherwise

        Raises:
            asyncio.TimeoutError: If connection times out
        """
        try:
            logger.info(f"[{self.client_id}] Connecting to {self.base_url}/socket.io/")

            await asyncio.wait_for(
                self.sio.connect(
                    f"{self.base_url}/socket.io/",
                    transports=['websocket']
                ),
                timeout=timeout
            )

            # Wait for connection_ready event
            await asyncio.wait_for(
                self._connection_ready.wait(),
                timeout=timeout
            )

            logger.info(
                f"[{self.client_id}] Connection established. "
                f"SID: {self.sid}, server_seq: {self.server_seq_on_connect}"
            )
            return True

        except asyncio.TimeoutError:
            logger.error(f"[{self.client_id}] Connection timeout after {timeout}s")
            raise
        except Exception as e:
            logger.error(f"[{self.client_id}] Connection error: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the Socket.IO server."""
        if self._is_connected:
            logger.info(f"[{self.client_id}] Disconnecting...")
            await self.sio.disconnect()
            self._is_connected = False

    async def join_room(self, room: str, **kwargs):
        """
        Join a Socket.IO room.

        Args:
            room: Room name (e.g., "playlists", "playlist", "nfc", "player")
            **kwargs: Additional parameters for join event (e.g., playlist_id)

        Examples:
            await client.join_room("playlists")
            await client.join_room("playlist", playlist_id="abc-123")
            await client.join_room("nfc")
        """
        event_name = f"join:{room}"
        payload = kwargs

        logger.info(f"[{self.client_id}] Joining room: {event_name} with payload: {payload}")
        await self.sio.emit(event_name, payload)

    async def leave_room(self, room: str, **kwargs):
        """
        Leave a Socket.IO room.

        Args:
            room: Room name
            **kwargs: Additional parameters
        """
        event_name = f"leave:{room}"
        payload = kwargs

        logger.info(f"[{self.client_id}] Leaving room: {event_name}")
        await self.sio.emit(event_name, payload)

    async def emit(self, event: str, data: Optional[Dict] = None):
        """
        Emit a custom event to the server.

        Args:
            event: Event name
            data: Event payload
        """
        logger.debug(f"[{self.client_id}] Emitting event: {event}")
        await self.sio.emit(event, data or {})

    async def wait_for_event(
        self,
        event_type: str,
        timeout: float = 5.0,
        predicate: Optional[Callable[[CapturedEvent], bool]] = None
    ) -> CapturedEvent:
        """
        Wait for a specific event to be received.

        Args:
            event_type: Type of event to wait for (e.g., "state:player")
            timeout: Maximum wait time in seconds
            predicate: Optional function to filter events (returns True to accept)

        Returns:
            The captured event

        Raises:
            asyncio.TimeoutError: If event not received within timeout

        Example:
            # Wait for any state:player event
            event = await client.wait_for_event("state:player", timeout=3.0)

            # Wait for specific playlist
            event = await client.wait_for_event(
                "state:playlists",
                predicate=lambda e: e.data.get("server_seq", 0) > 10
            )
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check if timeout exceeded
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise asyncio.TimeoutError(
                    f"Event '{event_type}' not received within {timeout}s. "
                    f"Captured {len(self.captured_events)} events total."
                )

            # Search through captured events
            for event in self.captured_events:
                if event.event_type == event_type:
                    if predicate is None or predicate(event):
                        logger.debug(
                            f"[{self.client_id}] Found matching event: {event_type}"
                        )
                        return event

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    async def wait_for_multiple_events(
        self,
        event_type: str,
        count: int,
        timeout: float = 5.0
    ) -> List[CapturedEvent]:
        """
        Wait for multiple instances of an event.

        Args:
            event_type: Type of event to wait for
            count: Number of events to wait for
            timeout: Maximum wait time in seconds

        Returns:
            List of captured events

        Raises:
            asyncio.TimeoutError: If not enough events received within timeout
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check if timeout exceeded
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                matching = [e for e in self.captured_events if e.event_type == event_type]
                raise asyncio.TimeoutError(
                    f"Only received {len(matching)}/{count} '{event_type}' events "
                    f"within {timeout}s"
                )

            # Count matching events
            matching = [e for e in self.captured_events if e.event_type == event_type]
            if len(matching) >= count:
                logger.debug(
                    f"[{self.client_id}] Received {count} '{event_type}' events"
                )
                return matching[:count]

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    def get_events(
        self,
        event_type: Optional[str] = None,
        since_timestamp: Optional[float] = None
    ) -> List[CapturedEvent]:
        """
        Get captured events, optionally filtered.

        Args:
            event_type: Filter by event type (None = all events)
            since_timestamp: Only return events after this timestamp

        Returns:
            List of matching captured events
        """
        events = self.captured_events

        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]

        if since_timestamp is not None:
            events = [e for e in events if e.timestamp >= since_timestamp]

        return events

    def clear_events(self):
        """Clear all captured events."""
        logger.debug(f"[{self.client_id}] Clearing {len(self.captured_events)} events")
        self.captured_events.clear()

    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback for a specific event type.

        Args:
            event_type: Event type to listen for
            callback: Function to call when event received (receives CapturedEvent)
        """
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)

    def assert_server_seq_increasing(self):
        """
        Assert that server_seq is monotonically increasing across all state events.

        Raises:
            AssertionError: If server_seq is not monotonically increasing
        """
        state_events = [
            e for e in self.captured_events
            if e.event_type.startswith('state:') and 'server_seq' in e.data
        ]

        if len(state_events) < 2:
            logger.warning(
                f"[{self.client_id}] Not enough state events to check server_seq "
                f"monotonicity (got {len(state_events)})"
            )
            return

        seqs = [e.data['server_seq'] for e in state_events]
        sorted_seqs = sorted(seqs)

        if seqs != sorted_seqs:
            raise AssertionError(
                f"server_seq not monotonically increasing: {seqs}. "
                f"Expected: {sorted_seqs}"
            )

        logger.info(
            f"[{self.client_id}] server_seq monotonicity validated: "
            f"{len(seqs)} events with seq range [{min(seqs)}, {max(seqs)}]"
        )

    def get_server_seq_range(self) -> tuple[Optional[int], Optional[int]]:
        """
        Get the range of server_seq values received.

        Returns:
            Tuple of (min_seq, max_seq) or (None, None) if no state events
        """
        state_events = [
            e for e in self.captured_events
            if e.event_type.startswith('state:') and 'server_seq' in e.data
        ]

        if not state_events:
            return (None, None)

        seqs = [e.data['server_seq'] for e in state_events]
        return (min(seqs), max(seqs))

    @property
    def is_connected(self) -> bool:
        """Check if client is currently connected."""
        return self._is_connected

    def __repr__(self) -> str:
        return (
            f"WebSocketTestClient(id={self.client_id}, "
            f"connected={self._is_connected}, "
            f"events={len(self.captured_events)})"
        )
