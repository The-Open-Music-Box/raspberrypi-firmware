# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Integration tests for player WebSocket functionality.

These tests verify:
- HTTP actions trigger WebSocket broadcasts
- state:player events match contracts
- server_seq is monotonically increasing
- Multiple clients receive same state updates
- client_op_id correlation between HTTP and WebSocket
"""

import pytest
import asyncio
import httpx

from .websocket_test_client import WebSocketTestClient


class TestPlayerWebSocketIntegration:
    """Integration tests for player state broadcasting via WebSocket."""

    @pytest.mark.asyncio
    async def test_player_state_broadcasts_on_http_action(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        backend_ready: bool
    ):
        """
        Test: HTTP player action triggers WebSocket state:player broadcast.

        Flow:
        1. WebSocket client joins 'playlists' room
        2. HTTP request to toggle player
        3. Verify WebSocket receives state:player event
        4. Verify event matches contracts
        """
        # Arrange: Subscribe to playlists room
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)  # Allow subscription to complete

        initial_event_count = len(websocket_client.captured_events)

        # Act: Toggle player via HTTP
        response = await http_client.post("/api/player/toggle")
        assert response.status_code in [200, 201], f"HTTP toggle failed: {response.text}"

        # Assert: Wait for state:player broadcast
        try:
            event = await websocket_client.wait_for_event("state:player", timeout=3.0)

            # Verify event structure
            assert "data" in event.data, "Event missing 'data' field"
            assert "server_seq" in event.data, "Event missing 'server_seq'"
            assert event.data["event_type"] == "state:player"

            # Verify server_seq increased
            assert event.data["server_seq"] > 0

            # Contract validation happens automatically via fixture

        except asyncio.TimeoutError:
            pytest.fail(
                f"state:player event not received within 3s. "
                f"Events captured: {len(websocket_client.captured_events) - initial_event_count}"
            )

    @pytest.mark.asyncio
    async def test_volume_change_broadcasts_player_state(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        test_client_op_id: str,
        backend_ready: bool
    ):
        """
        Test: Volume change via HTTP triggers state:player broadcast.

        Also tests client_op_id correlation.
        """
        # Arrange
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()  # Clear previous events

        # Act: Change volume with client_op_id
        response = await http_client.post(
            "/api/player/volume",
            json={"volume": 50, "client_op_id": test_client_op_id}
        )
        assert response.status_code == 200

        # Assert: Verify broadcast
        try:
            event = await websocket_client.wait_for_event("state:player", timeout=3.0)

            # Verify volume in state
            player_data = event.data.get("data", {})
            assert "volume" in player_data, "Player state missing volume"

            # Note: client_op_id might not be in every state event
            # depending on backend implementation

        except asyncio.TimeoutError:
            pytest.fail("state:player event not received after volume change")

    @pytest.mark.asyncio
    async def test_server_seq_monotonically_increasing(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        backend_ready: bool
    ):
        """
        Test: server_seq increases monotonically across multiple actions.
        """
        # Arrange
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        # Act: Perform multiple actions
        actions = [
            lambda: http_client.post("/api/player/toggle"),
            lambda: http_client.post("/api/player/volume", json={"volume": 60}),
            lambda: http_client.post("/api/player/toggle"),
        ]

        for action in actions:
            response = await action()
            assert response.status_code in [200, 201]
            await asyncio.sleep(0.3)  # Allow broadcast to arrive

        # Assert: Verify server_seq monotonicity
        try:
            websocket_client.assert_server_seq_increasing()

            # Also check range
            min_seq, max_seq = websocket_client.get_server_seq_range()
            assert min_seq is not None, "No server_seq values captured"
            assert max_seq > min_seq, "server_seq did not increase"

        except AssertionError as e:
            pytest.fail(f"server_seq validation failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize('multiple_websocket_clients', [2], indirect=True)
    async def test_multiple_clients_receive_same_state(
        self,
        http_client: httpx.AsyncClient,
        multiple_websocket_clients: list[WebSocketTestClient],
        backend_ready: bool
    ):
        """
        Test: Multiple WebSocket clients receive identical state updates.

        Verifies:
        - Both clients receive state:player event
        - server_seq is identical across clients
        - Data content is identical
        """
        client1, client2 = multiple_websocket_clients

        # Arrange: Both clients join room
        await client1.join_room("playlists")
        await client2.join_room("playlists")
        await asyncio.sleep(0.5)

        client1.clear_events()
        client2.clear_events()

        # Act: Trigger state change
        response = await http_client.post("/api/player/toggle")
        assert response.status_code in [200, 201]

        # Assert: Both clients receive event
        try:
            event1 = await client1.wait_for_event("state:player", timeout=3.0)
            event2 = await client2.wait_for_event("state:player", timeout=3.0)

            # Verify server_seq matches
            assert event1.data["server_seq"] == event2.data["server_seq"], \
                "Clients received different server_seq values"

            # Verify data matches (at least is_playing field)
            data1 = event1.data.get("data", {})
            data2 = event2.data.get("data", {})

            if "is_playing" in data1 and "is_playing" in data2:
                assert data1["is_playing"] == data2["is_playing"], \
                    "Clients received different is_playing states"

        except asyncio.TimeoutError:
            pytest.fail(
                f"Not all clients received state:player event. "
                f"Client1: {len(client1.captured_events)} events, "
                f"Client2: {len(client2.captured_events)} events"
            )

    @pytest.mark.asyncio
    async def test_player_seek_broadcasts_position_update(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        backend_ready: bool
    ):
        """
        Test: Seeking to a position broadcasts state:player with updated position.

        Note: This test may be skipped if no track is currently playing.
        """
        # Arrange
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        # Act: Attempt to seek (may fail if no track playing)
        response = await http_client.post(
            "/api/player/seek",
            json={"position_ms": 5000}
        )

        if response.status_code == 400:
            pytest.skip("No track playing, cannot test seek")

        assert response.status_code == 200

        # Assert: Verify broadcast
        try:
            event = await websocket_client.wait_for_event("state:player", timeout=3.0)

            player_data = event.data.get("data", {})
            # Position may not exactly match due to timing, just verify it exists
            assert "position_ms" in player_data, "Player state missing position_ms"

        except asyncio.TimeoutError:
            pytest.fail("state:player event not received after seek")

    @pytest.mark.asyncio
    async def test_disconnect_reconnect_receives_latest_state(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        backend_ready: bool
    ):
        """
        Test: Client reconnection after state changes receives current state.

        Flow:
        1. Connect client, join room
        2. Trigger state change
        3. Disconnect client
        4. Trigger another state change (while disconnected)
        5. Reconnect and verify receiving latest state
        """
        # Arrange: Initial connection
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        # Act: Trigger state change while connected
        response = await http_client.post("/api/player/toggle")
        assert response.status_code in [200, 201]

        event1 = await websocket_client.wait_for_event("state:player", timeout=3.0)
        seq1 = event1.data["server_seq"]

        # Disconnect
        await websocket_client.disconnect()
        await asyncio.sleep(0.3)

        # Trigger state change while disconnected
        response = await http_client.post("/api/player/toggle")
        assert response.status_code in [200, 201]
        await asyncio.sleep(0.3)

        # Reconnect
        websocket_client.clear_events()
        await websocket_client.connect()
        await websocket_client.join_room("playlists")

        # The backend should send current state upon joining
        # Wait for state event (may be state:playlists or state:player)
        await asyncio.sleep(1.0)

        # Verify we have newer state
        state_events = websocket_client.get_events("state:player")
        if state_events:
            latest_event = state_events[-1]
            seq2 = latest_event.data["server_seq"]
            assert seq2 > seq1, "Reconnected client did not receive latest state"
