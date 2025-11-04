# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Pytest fixtures for WebSocket integration tests.

This module provides reusable fixtures for testing Socket.IO functionality,
including backend server management, WebSocket clients, and contract validation.
"""

import pytest
import asyncio
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional

from .websocket_test_client import WebSocketTestClient
from .contract_validator import ContractValidator


# Backend server configuration
BACKEND_URL = "http://localhost:8000"
CONTRACTS_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "contracts" / "schemas" / "socketio_contracts.json"


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.

    This ensures all async tests use the same event loop.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def contract_validator():
    """
    Create a contract validator instance (session-scoped).

    Returns:
        ContractValidator instance configured with Socket.IO contracts
    """
    if not CONTRACTS_SCHEMA_PATH.exists():
        pytest.skip(
            f"Socket.IO contracts not found at {CONTRACTS_SCHEMA_PATH}. "
            "Ensure contracts repo is checked out."
        )

    return ContractValidator(str(CONTRACTS_SCHEMA_PATH), strict=True)


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Create an async HTTP client for testing HTTP endpoints.

    Yields:
        httpx.AsyncClient configured for backend
    """
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
async def websocket_client(
    contract_validator: ContractValidator
) -> AsyncGenerator[WebSocketTestClient, None]:
    """
    Create a WebSocket test client with automatic contract validation.

    Yields:
        Connected WebSocketTestClient instance

    Example usage:
        async def test_player_state(websocket_client):
            await websocket_client.join_room("playlists")
            event = await websocket_client.wait_for_event("state:player")
            assert event.data["server_seq"] > 0
    """
    client = WebSocketTestClient(
        base_url=BACKEND_URL,
        contract_validator=contract_validator,
        auto_validate=True
    )

    try:
        await client.connect(timeout=10.0)
        yield client
    finally:
        await client.disconnect()


@pytest.fixture
async def websocket_client_no_validation() -> AsyncGenerator[WebSocketTestClient, None]:
    """
    Create a WebSocket test client WITHOUT automatic contract validation.

    Useful for testing edge cases or invalid contracts.

    Yields:
        Connected WebSocketTestClient instance without validation
    """
    client = WebSocketTestClient(
        base_url=BACKEND_URL,
        auto_validate=False
    )

    try:
        await client.connect(timeout=10.0)
        yield client
    finally:
        await client.disconnect()


@pytest.fixture
async def multiple_websocket_clients(
    contract_validator: ContractValidator,
    request
) -> AsyncGenerator[list[WebSocketTestClient], None]:
    """
    Create multiple WebSocket test clients for multi-client tests.

    Usage:
        @pytest.mark.parametrize('multiple_websocket_clients', [2], indirect=True)
        async def test_multi_client(multiple_websocket_clients):
            client1, client2 = multiple_websocket_clients
            # Test synchronization between clients...

    Args:
        request: Pytest request object with param specifying number of clients

    Yields:
        List of connected WebSocketTestClient instances
    """
    num_clients = getattr(request, 'param', 2)  # Default to 2 clients
    clients = []

    try:
        # Create and connect all clients
        for i in range(num_clients):
            client = WebSocketTestClient(
                base_url=BACKEND_URL,
                client_id=f"test-client-{i+1}",
                contract_validator=contract_validator,
                auto_validate=True
            )
            await client.connect(timeout=10.0)
            clients.append(client)

        yield clients

    finally:
        # Disconnect all clients
        for client in clients:
            await client.disconnect()


@pytest.fixture
async def backend_ready(http_client: httpx.AsyncClient) -> bool:
    """
    Check if backend is ready to accept requests.

    Returns:
        True if backend is ready, False otherwise

    Raises:
        pytest.skip: If backend is not reachable
    """
    try:
        response = await http_client.get("/api/health")
        if response.status_code == 200:
            return True
    except Exception as e:
        pytest.skip(f"Backend not reachable at {BACKEND_URL}: {e}")

    return False


@pytest.fixture
async def clean_state(http_client: httpx.AsyncClient):
    """
    Ensure backend is in a clean state before test.

    This fixture can be expanded to reset playlists, NFC associations, etc.
    """
    # Currently a placeholder - expand as needed
    # For example, could delete all test playlists, clear NFC associations, etc.
    yield
    # Cleanup after test if needed


@pytest.fixture
def test_playlist_data():
    """
    Provide sample playlist data for tests.

    Returns:
        Dictionary with test playlist data
    """
    return {
        "name": "Test Integration Playlist",
        "description": "Created by integration tests"
    }


@pytest.fixture
def test_client_op_id():
    """
    Generate a unique client_op_id for test operations.

    Returns:
        Unique client operation ID string
    """
    import uuid
    return f"test-op-{uuid.uuid4()}"


# Utility function for parametrized multi-client tests
def pytest_generate_tests(metafunc):
    """
    Custom test generation for multi-client tests.

    Allows tests to specify number of clients via indirect parametrization.
    """
    if 'multiple_websocket_clients' in metafunc.fixturenames:
        # Check if test has explicit parametrization
        if not hasattr(metafunc.function, 'pytestmark'):
            # Default to 2 clients if not specified
            metafunc.parametrize('multiple_websocket_clients', [2], indirect=True)
