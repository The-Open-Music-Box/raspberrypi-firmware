# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for EventOutbox retry mechanism."""

import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.src.services.event_outbox import EventOutbox, OutboxEvent


@pytest.fixture
def mock_socketio():
    """Create a mock Socket.IO server."""
    sio = AsyncMock()
    sio.emit = AsyncMock()
    return sio


@pytest.fixture
def outbox(mock_socketio):
    """Create an EventOutbox with mocked socketio and config."""
    with patch("app.src.services.event_outbox.socket_config") as mock_config:
        mock_config.OUTBOX_RETRY_MAX = 3
        mock_config.OUTBOX_SIZE_LIMIT = 1000
        mock_config.OUTBOX_CLEANUP_BATCH = 100
        ob = EventOutbox(socketio_server=mock_socketio)
    return ob


def _make_event(
    event_id="evt-1",
    event_type="state:playlists",
    payload=None,
    server_seq=1,
    retry_count=0,
    playlist_id=None,
):
    """Helper to create an OutboxEvent."""
    return OutboxEvent(
        event_id=event_id,
        event_type=event_type,
        payload=payload or {"data": "test"},
        server_seq=server_seq,
        retry_count=retry_count,
        playlist_id=playlist_id,
    )


class TestProcessOutboxEmitsEventsSuccessfully:
    """All events emitted, outbox cleared."""

    @pytest.mark.asyncio
    async def test_process_outbox_emits_events_successfully(self, outbox, mock_socketio):
        """When all events emit successfully, outbox should be empty afterward."""
        # Add events to the outbox
        outbox._outbox = [
            _make_event(event_id="e1", server_seq=1),
            _make_event(event_id="e2", server_seq=2),
        ]

        with patch(
            "app.src.common.socket_events.SocketEventType",
            side_effect=lambda v: v,
        ), patch(
            "app.src.common.socket_events.get_event_room",
            return_value="playlists",
        ):
            await outbox.process_outbox()

        assert mock_socketio.emit.call_count == 2
        assert len(outbox._outbox) == 0


class TestProcessOutboxRetriesFailedEvents:
    """Emit raises, event goes back with incremented retry_count."""

    @pytest.mark.asyncio
    async def test_process_outbox_retries_failed_events(self, outbox, mock_socketio):
        """When emit fails, event should be re-queued with incremented retry_count."""
        event = _make_event(event_id="fail-1", retry_count=0)
        outbox._outbox = [event]

        mock_socketio.emit.side_effect = ConnectionError("Network error")

        with patch(
            "app.src.common.socket_events.SocketEventType",
            side_effect=lambda v: v,
        ), patch(
            "app.src.common.socket_events.get_event_room",
            return_value="playlists",
        ):
            await outbox.process_outbox()

        # Event should be back in outbox with incremented retry_count
        assert len(outbox._outbox) == 1
        assert outbox._outbox[0].event_id == "fail-1"
        assert outbox._outbox[0].retry_count == 1


class TestProcessOutboxDropsEventsAfterMaxRetries:
    """Event exceeds max retries, not retried."""

    @pytest.mark.asyncio
    async def test_process_outbox_drops_events_after_max_retries(self, outbox, mock_socketio):
        """When event has reached max retries, it should be dropped permanently."""
        # retry_count=2 means next failure will be attempt 3 (== max_retry_count)
        event = _make_event(event_id="drop-1", retry_count=2)
        outbox._outbox = [event]

        mock_socketio.emit.side_effect = ConnectionError("Network error")

        with patch(
            "app.src.common.socket_events.SocketEventType",
            side_effect=lambda v: v,
        ), patch(
            "app.src.common.socket_events.get_event_room",
            return_value="playlists",
        ):
            await outbox.process_outbox()

        # Event should be dropped, outbox empty
        assert len(outbox._outbox) == 0


class TestProcessOutboxLogsSuccessOnlyOnSuccess:
    """Verify logging behavior."""

    @pytest.mark.asyncio
    async def test_process_outbox_logs_success_only_on_success(self, outbox, mock_socketio, caplog):
        """Success log should only appear for successfully emitted events."""
        success_event = _make_event(event_id="ok-1", server_seq=1)
        fail_event = _make_event(event_id="fail-1", server_seq=2)
        outbox._outbox = [success_event, fail_event]

        # First call succeeds, second raises
        call_count = 0

        async def emit_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ConnectionError("Network error")

        mock_socketio.emit.side_effect = emit_side_effect

        with patch(
            "app.src.common.socket_events.SocketEventType",
            side_effect=lambda v: v,
        ), patch(
            "app.src.common.socket_events.get_event_room",
            return_value="playlists",
        ):
            with caplog.at_level(logging.DEBUG, logger="app.src.services.event_outbox"):
                await outbox.process_outbox()

        # "Successfully emitted" should appear for ok-1 only
        success_msgs = [r for r in caplog.records if "Successfully emitted" in r.message]
        assert len(success_msgs) == 1
        assert "ok-1" in success_msgs[0].message

        # Warning for failed event
        warning_msgs = [r for r in caplog.records if "Failed to emit" in r.message]
        assert len(warning_msgs) == 1
        assert "fail-1" in warning_msgs[0].message


class TestProcessOutboxEmptyNoop:
    """No events, early return."""

    @pytest.mark.asyncio
    async def test_process_outbox_empty_noop(self, outbox, mock_socketio):
        """When outbox is empty, process should return early without emitting."""
        outbox._outbox = []

        await outbox.process_outbox()

        mock_socketio.emit.assert_not_called()


class TestProcessOutboxNoSocketioNoop:
    """socketio is None, early return."""

    @pytest.mark.asyncio
    async def test_process_outbox_no_socketio_noop(self):
        """When socketio is None, process should return early."""
        with patch("app.src.services.event_outbox.socket_config") as mock_config:
            mock_config.OUTBOX_RETRY_MAX = 3
            mock_config.OUTBOX_SIZE_LIMIT = 1000
            mock_config.OUTBOX_CLEANUP_BATCH = 100
            ob = EventOutbox(socketio_server=None)

        event = _make_event(event_id="should-not-emit")
        ob._outbox = [event]

        await ob.process_outbox()

        # Event should still be in outbox (not processed)
        assert len(ob._outbox) == 1
