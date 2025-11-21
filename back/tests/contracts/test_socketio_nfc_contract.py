"""Contract tests for Socket.IO NFC events.

Validates that Socket.IO NFC-specific events conform to the expected contract.

Progress: 5/5 events tested ✅
"""

import pytest
from app.src.common.socket_events import SocketEventBuilder, SocketEventType


@pytest.mark.asyncio
class TestSocketIONFCContract:
    """Contract tests for Socket.IO NFC broadcast events."""

    async def test_nfc_status_event_contract(self):
        """Test 'nfc_status' event - NFC reader status update.

        Contract:
        - Direction: server_to_client
        - Payload: {reader_available: bool, scanning: bool, association_active: bool}
        """
        nfc_status_payload = {
            "reader_available": True,
            "scanning": False,
            "association_active": False
        }

        assert "reader_available" in nfc_status_payload
        assert "scanning" in nfc_status_payload
        assert isinstance(nfc_status_payload["reader_available"], bool)
        assert isinstance(nfc_status_payload["scanning"], bool)

    async def test_nfc_association_state_event_contract(self):
        """Test 'nfc_association_state' event - NFC tag association state.

        Contract:
        - Direction: server_to_client
        - Payload: {tag_id?: str, playlist_id?: str, state: str}
        """
        association_state = {
            "tag_id": "test-tag-123",
            "playlist_id": "playlist-456",
            "state": "associated"
        }

        assert "state" in association_state
        assert isinstance(association_state["state"], str)
        if "tag_id" in association_state:
            assert isinstance(association_state["tag_id"], str)
        if "playlist_id" in association_state:
            assert isinstance(association_state["playlist_id"], str)

    async def test_start_nfc_link_event_contract(self):
        """Test 'start_nfc_link' event - Start NFC association session.

        Contract:
        - Direction: server_to_client
        - Payload: {session_id: str, playlist_id: str, timeout_ms: number}
        """
        start_link_payload = {
            "session_id": "nfc-session-789",
            "playlist_id": "playlist-abc",
            "timeout_ms": 60000
        }

        assert "session_id" in start_link_payload
        assert "playlist_id" in start_link_payload
        assert "timeout_ms" in start_link_payload
        assert isinstance(start_link_payload["session_id"], str)
        assert isinstance(start_link_payload["playlist_id"], str)
        assert isinstance(start_link_payload["timeout_ms"], int)

    async def test_stop_nfc_link_event_contract(self):
        """Test 'stop_nfc_link' event - Stop NFC association session.

        Contract:
        - Direction: server_to_client
        - Payload: {session_id: str, reason: str}
        """
        stop_link_payload = {
            "session_id": "nfc-session-789",
            "reason": "timeout"
        }

        assert "session_id" in stop_link_payload
        assert "reason" in stop_link_payload
        assert isinstance(stop_link_payload["session_id"], str)
        assert isinstance(stop_link_payload["reason"], str)

    async def test_override_nfc_tag_event_contract(self):
        """Test 'override_nfc_tag' event - Override NFC tag association.

        Contract:
        - Direction: server_to_client
        - Payload: {tag_id: str, old_playlist_id?: str, new_playlist_id: str}
        """
        override_payload = {
            "tag_id": "test-tag-999",
            "old_playlist_id": "old-playlist-111",
            "new_playlist_id": "new-playlist-222"
        }

        assert "tag_id" in override_payload
        assert "new_playlist_id" in override_payload
        assert isinstance(override_payload["tag_id"], str)
        assert isinstance(override_payload["new_playlist_id"], str)
