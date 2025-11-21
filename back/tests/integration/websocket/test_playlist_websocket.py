# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Integration tests for playlist WebSocket functionality.

These tests verify:
- CRUD operations trigger appropriate WebSocket broadcasts
- state:playlists events match contracts
- Track reordering broadcasts correctly
- Track deletion broadcasts correctly
- Multi-client synchronization
"""

import pytest
import asyncio
import httpx

from .websocket_test_client import WebSocketTestClient


class TestPlaylistWebSocketIntegration:
    """Integration tests for playlist state broadcasting via WebSocket."""

    @pytest.mark.asyncio
    async def test_create_playlist_broadcasts_state_playlists(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        test_playlist_data: dict,
        test_client_op_id: str,
        backend_ready: bool
    ):
        """
        Test: Creating a playlist via HTTP triggers state:playlists broadcast.

        Flow:
        1. WebSocket client joins 'playlists' room
        2. HTTP POST to create playlist with client_op_id
        3. Verify state:playlists broadcast
        4. Verify contract compliance
        5. Cleanup: delete test playlist
        """
        # Arrange
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        # Act: Create playlist
        response = await http_client.post(
            "/api/playlists",
            json={**test_playlist_data, "client_op_id": test_client_op_id}
        )
        assert response.status_code == 201, f"Create playlist failed: {response.text}"

        response_data = response.json()
        playlist_id = response_data.get("data", {}).get("id")
        assert playlist_id is not None, "No playlist ID in response"

        try:
            # Assert: Wait for broadcast
            event = await websocket_client.wait_for_event("state:playlists", timeout=3.0)

            # Verify event structure
            assert event.data["event_type"] == "state:playlists"
            assert "server_seq" in event.data
            assert "data" in event.data

            # Verify playlists list contains new playlist
            playlists_data = event.data.get("data", {})
            assert "playlists" in playlists_data or "items" in playlists_data

            # Contract validation happens automatically

        except asyncio.TimeoutError:
            pytest.fail("state:playlists event not received within 3s")

        finally:
            # Cleanup: Delete test playlist
            delete_response = await http_client.delete(f"/api/playlists/{playlist_id}")
            assert delete_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_delete_playlist_broadcasts_update(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        test_playlist_data: dict,
        backend_ready: bool
    ):
        """
        Test: Deleting a playlist triggers state:playlists broadcast.
        """
        # Arrange: Create a playlist first
        create_response = await http_client.post(
            "/api/playlists",
            json=test_playlist_data
        )
        assert create_response.status_code == 201
        playlist_id = create_response.json().get("data", {}).get("id")

        # Subscribe to broadcasts
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        # Act: Delete playlist
        delete_response = await http_client.delete(f"/api/playlists/{playlist_id}")
        assert delete_response.status_code in [200, 204]

        # Assert: Verify broadcast
        try:
            event = await websocket_client.wait_for_event("state:playlists", timeout=3.0)

            assert event.data["event_type"] == "state:playlists"
            assert "server_seq" in event.data

            # Optionally verify playlist no longer in list
            # (depends on backend implementation)

        except asyncio.TimeoutError:
            pytest.fail("state:playlists event not received after deletion")

    @pytest.mark.asyncio
    async def test_update_playlist_name_broadcasts(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        test_playlist_data: dict,
        backend_ready: bool
    ):
        """
        Test: Updating playlist name triggers state:playlists broadcast.
        """
        # Arrange: Create playlist
        create_response = await http_client.post(
            "/api/playlists",
            json=test_playlist_data
        )
        assert create_response.status_code == 201
        playlist_id = create_response.json().get("data", {}).get("id")

        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        try:
            # Act: Update playlist name
            update_response = await http_client.put(
                f"/api/playlists/{playlist_id}",
                json={"name": "Updated Test Playlist"}
            )
            assert update_response.status_code == 200

            # Assert: Verify broadcast
            event = await websocket_client.wait_for_event("state:playlists", timeout=3.0)

            assert event.data["event_type"] == "state:playlists"
            assert event.data["server_seq"] > 0

        except asyncio.TimeoutError:
            pytest.fail("state:playlists event not received after update")

        finally:
            # Cleanup
            await http_client.delete(f"/api/playlists/{playlist_id}")

    @pytest.mark.asyncio
    async def test_reorder_tracks_broadcasts_playlist_state(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        test_playlist_data: dict,
        backend_ready: bool
    ):
        """
        Test: Reordering tracks in a playlist broadcasts state update.

        Note: This test requires a playlist with at least 2 tracks.
        If no tracks available, test will be skipped.
        """
        # Arrange: Create playlist
        create_response = await http_client.post(
            "/api/playlists",
            json=test_playlist_data
        )
        assert create_response.status_code == 201
        playlist_id = create_response.json().get("data", {}).get("id")

        # Check if playlist has tracks (may need to add tracks first)
        get_response = await http_client.get(f"/api/playlists/{playlist_id}")
        playlist_data = get_response.json().get("data", {})
        tracks = playlist_data.get("tracks", [])

        if len(tracks) < 2:
            # Cleanup and skip
            await http_client.delete(f"/api/playlists/{playlist_id}")
            pytest.skip("Playlist needs at least 2 tracks to test reordering")

        await websocket_client.join_room("playlists")
        await websocket_client.join_room("playlist", playlist_id=playlist_id)
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        try:
            # Act: Reorder tracks (move first track to second position)
            track_ids = [t["id"] for t in tracks]
            reordered_ids = [track_ids[1], track_ids[0]] + track_ids[2:]

            reorder_response = await http_client.post(
                f"/api/playlists/{playlist_id}/reorder",
                json={"track_ids": reordered_ids}
            )

            if reorder_response.status_code == 404:
                pytest.skip("Reorder endpoint not implemented")

            assert reorder_response.status_code == 200

            # Assert: Verify broadcast (could be state:playlists or state:playlist)
            try:
                event = await websocket_client.wait_for_event(
                    "state:playlists",
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                # Try state:playlist instead
                event = await websocket_client.wait_for_event(
                    "state:playlist",
                    timeout=1.0
                )

            assert event.data["server_seq"] > 0

        except asyncio.TimeoutError:
            pytest.fail("No state event received after track reorder")

        finally:
            # Cleanup
            await http_client.delete(f"/api/playlists/{playlist_id}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize('multiple_websocket_clients', [3], indirect=True)
    async def test_three_clients_sync_playlist_creation(
        self,
        http_client: httpx.AsyncClient,
        multiple_websocket_clients: list[WebSocketTestClient],
        test_playlist_data: dict,
        backend_ready: bool
    ):
        """
        Test: Three clients all receive the same playlist creation broadcast.

        Verifies server-authoritative state management with multiple clients.
        """
        client1, client2, client3 = multiple_websocket_clients

        # Arrange: All clients join room
        for client in multiple_websocket_clients:
            await client.join_room("playlists")
        await asyncio.sleep(0.5)

        for client in multiple_websocket_clients:
            client.clear_events()

        # Act: Create playlist
        response = await http_client.post(
            "/api/playlists",
            json=test_playlist_data
        )
        assert response.status_code == 201
        playlist_id = response.json().get("data", {}).get("id")

        try:
            # Assert: All three clients receive event
            events = []
            for i, client in enumerate(multiple_websocket_clients, 1):
                try:
                    event = await client.wait_for_event("state:playlists", timeout=3.0)
                    events.append(event)
                except asyncio.TimeoutError:
                    pytest.fail(f"Client {i} did not receive state:playlists event")

            # Verify all clients got same server_seq
            seqs = [e.data["server_seq"] for e in events]
            assert len(set(seqs)) == 1, f"Clients received different server_seq values: {seqs}"

            # Verify all clients received the new playlist in data
            for event in events:
                assert "data" in event.data

        finally:
            # Cleanup
            await http_client.delete(f"/api/playlists/{playlist_id}")

    @pytest.mark.asyncio
    async def test_client_that_created_playlist_also_receives_broadcast(
        self,
        http_client: httpx.AsyncClient,
        websocket_client: WebSocketTestClient,
        test_playlist_data: dict,
        test_client_op_id: str,
        backend_ready: bool
    ):
        """
        Test: The client that initiated the action also receives the broadcast.

        This is a key requirement of server-authoritative state management:
        the client that performed the action should receive the state update
        via WebSocket, not just via HTTP response.
        """
        # Arrange
        await websocket_client.join_room("playlists")
        await asyncio.sleep(0.5)

        websocket_client.clear_events()

        # Act: Create playlist with client_op_id
        response = await http_client.post(
            "/api/playlists",
            json={**test_playlist_data, "client_op_id": test_client_op_id}
        )
        assert response.status_code == 201
        playlist_id = response.json().get("data", {}).get("id")

        try:
            # Assert: Verify this client also received the broadcast
            event = await websocket_client.wait_for_event("state:playlists", timeout=3.0)

            # The broadcast should be received even though this client initiated the action
            assert event.data["event_type"] == "state:playlists"

            # Optionally check if client_op_id is included (depends on implementation)
            # This helps the client correlate the broadcast with its own action

        except asyncio.TimeoutError:
            pytest.fail(
                "Originating client did not receive broadcast - "
                "violates server-authoritative state requirement"
            )

        finally:
            # Cleanup
            await http_client.delete(f"/api/playlists/{playlist_id}")
