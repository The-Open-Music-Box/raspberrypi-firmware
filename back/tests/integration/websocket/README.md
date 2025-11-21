# WebSocket Integration Tests

Integration tests for TheOpenMusicBox Socket.IO functionality with automatic contract validation.

## Overview

These tests verify real-time WebSocket communication between clients and the backend:

- **HTTP → WebSocket flow**: HTTP actions trigger WebSocket broadcasts
- **Contract compliance**: Events match OpenAPI and Socket.IO schemas
- **Multi-client sync**: Multiple clients receive identical state updates
- **server_seq monotonicity**: Sequence numbers increase consistently
- **client_op_id correlation**: Operations tracked across HTTP and WebSocket

## Structure

```
websocket/
├── __init__.py
├── README.md (this file)
├── conftest.py                    # Pytest fixtures
├── websocket_test_client.py       # Reusable WebSocket client
├── contract_validator.py          # Contract validation against schemas
├── test_player_websocket.py       # Player state tests
└── test_playlist_websocket.py     # Playlist state tests
```

## Prerequisites

### 1. Backend Running

Tests require the backend server to be running:

```bash
cd rpi-firmware/back
python -m uvicorn app.main:app --reload
```

By default, tests connect to `http://localhost:8000`.

### 2. Dependencies

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

Key dependencies:
- `pytest>=7.4.0`
- `pytest-asyncio>=0.21.0`
- `httpx>=0.24.0`
- `python-socketio>=5.9.0` (already in requirements.txt)
- `jsonschema>=4.20.0` (for contract validation)

### 3. Contracts Repository

Tests require the `contracts` repository to be checked out:

```
theopenmusicbox/
├── contracts/
│   └── schemas/
│       ├── openapi.yaml
│       └── socketio_contracts.json
└── rpi-firmware/
    └── back/
        └── tests/
            └── integration/
                └── websocket/
```

The `conftest.py` automatically locates contracts at:
`../../../../../contracts/schemas/socketio_contracts.json`

## Running Tests

### Run All WebSocket Tests

```bash
cd rpi-firmware/back
pytest tests/integration/websocket/ -v
```

### Run Specific Test File

```bash
# Player tests only
pytest tests/integration/websocket/test_player_websocket.py -v

# Playlist tests only
pytest tests/integration/websocket/test_playlist_websocket.py -v
```

### Run Specific Test

```bash
pytest tests/integration/websocket/test_player_websocket.py::TestPlayerWebSocketIntegration::test_player_state_broadcasts_on_http_action -v
```

### Run with Detailed Logging

```bash
pytest tests/integration/websocket/ -v --log-cli-level=DEBUG
```

### Run Only Multi-Client Tests

```bash
pytest tests/integration/websocket/ -v -k "multiple_clients"
```

## Test Examples

### Basic Player Test

```python
@pytest.mark.asyncio
async def test_player_toggle(
    http_client: httpx.AsyncClient,
    websocket_client: WebSocketTestClient,
    backend_ready: bool
):
    # Arrange: Subscribe to updates
    await websocket_client.join_room("playlists")

    # Act: Toggle player via HTTP
    response = await http_client.post("/api/player/toggle")
    assert response.status_code == 200

    # Assert: Verify WebSocket broadcast
    event = await websocket_client.wait_for_event("state:player", timeout=3.0)
    assert event.data["server_seq"] > 0

    # Contract validation happens automatically
```

### Multi-Client Test

```python
@pytest.mark.asyncio
@pytest.mark.parametrize('multiple_websocket_clients', [2], indirect=True)
async def test_two_clients_sync(
    http_client: httpx.AsyncClient,
    multiple_websocket_clients: list[WebSocketTestClient],
    backend_ready: bool
):
    client1, client2 = multiple_websocket_clients

    # Both clients join
    await client1.join_room("playlists")
    await client2.join_room("playlists")

    # Trigger action
    await http_client.post("/api/player/toggle")

    # Both receive same event
    event1 = await client1.wait_for_event("state:player", timeout=3.0)
    event2 = await client2.wait_for_event("state:player", timeout=3.0)

    assert event1.data["server_seq"] == event2.data["server_seq"]
```

### Contract Validation Test

```python
@pytest.mark.asyncio
async def test_event_matches_contract(
    websocket_client: WebSocketTestClient,
    contract_validator: ContractValidator
):
    await websocket_client.join_room("playlists")

    # Trigger some action...

    # Get events
    events = websocket_client.get_events("state:player")

    # Manually validate if needed (auto-validation also happens)
    for event in events:
        contract_validator.validate_event("state:player", event.data)

    # Validate server_seq monotonicity
    contract_validator.validate_server_seq_monotonic(events)
```

## Fixtures

### `websocket_client`

Single WebSocket client with automatic contract validation.

```python
async def test_example(websocket_client: WebSocketTestClient):
    await websocket_client.join_room("playlists")
    event = await websocket_client.wait_for_event("state:player")
```

### `websocket_client_no_validation`

WebSocket client WITHOUT automatic validation (for testing invalid contracts).

```python
async def test_invalid_event(websocket_client_no_validation: WebSocketTestClient):
    # Test events that may not match contracts
    ...
```

### `multiple_websocket_clients`

Multiple clients for multi-client synchronization tests.

```python
@pytest.mark.parametrize('multiple_websocket_clients', [3], indirect=True)
async def test_three_clients(multiple_websocket_clients: list[WebSocketTestClient]):
    client1, client2, client3 = multiple_websocket_clients
    ...
```

### `http_client`

Async HTTP client for triggering actions.

```python
async def test_http(http_client: httpx.AsyncClient):
    response = await http_client.post("/api/player/toggle")
    assert response.status_code == 200
```

### `contract_validator`

Contract validator for manual validation.

```python
def test_validate(contract_validator: ContractValidator):
    contract_validator.validate_event("state:player", event_data)
    contract_validator.validate_server_seq_monotonic(events)
```

### `backend_ready`

Ensures backend is reachable before running test.

```python
async def test_requires_backend(backend_ready: bool):
    # Test only runs if backend responds to /api/health
    ...
```

## WebSocketTestClient API

### Connection Management

```python
client = WebSocketTestClient("http://localhost:8000")

await client.connect()           # Connect to server
await client.disconnect()        # Disconnect
client.is_connected             # Check connection status
```

### Room Management

```python
await client.join_room("playlists")                           # Join global playlists room
await client.join_room("playlist", playlist_id="abc-123")     # Join specific playlist
await client.join_room("nfc")                                 # Join NFC room
await client.leave_room("playlists")                          # Leave room
```

### Event Handling

```python
# Wait for specific event
event = await client.wait_for_event("state:player", timeout=5.0)

# Wait with predicate
event = await client.wait_for_event(
    "state:player",
    predicate=lambda e: e.data.get("server_seq", 0) > 100
)

# Wait for multiple events
events = await client.wait_for_multiple_events("state:player", count=3, timeout=10.0)

# Get all captured events
all_events = client.get_events()

# Get filtered events
player_events = client.get_events("state:player")
recent_events = client.get_events(since_timestamp=start_time)

# Clear events
client.clear_events()
```

### Validation

```python
# Assert server_seq monotonicity
client.assert_server_seq_increasing()

# Get server_seq range
min_seq, max_seq = client.get_server_seq_range()
```

### Custom Callbacks

```python
def my_callback(event: CapturedEvent):
    print(f"Received: {event.event_type}")

client.register_callback("state:player", my_callback)
```

## ContractValidator API

### Validation

```python
validator = ContractValidator("/path/to/socketio_contracts.json")

# Validate single event
validator.validate_event("state:player", event_data)

# Validate server_seq monotonicity
validator.validate_server_seq_monotonic(events)

# Validate client_op_id correlation
validator.validate_client_op_id_correlation(
    "my-op-id",
    http_response,
    websocket_event
)
```

### Schema Inspection

```python
# Get schema for event
schema = validator.get_event_schema("state:player")

# List all event types
event_types = validator.list_event_types()
```

## Troubleshooting

### Backend Not Reachable

**Error**: `pytest.skip: Backend not reachable at http://localhost:8000`

**Solution**: Start the backend:
```bash
cd rpi-firmware/back
python -m uvicorn app.main:app
```

### Contract File Not Found

**Error**: `FileNotFoundError: Contract file not found`

**Solution**: Ensure contracts repository is checked out:
```bash
cd theopenmusicbox
git clone https://github.com/The-Open-Music-Box/contracts.git
```

### Connection Timeout

**Error**: `asyncio.TimeoutError: Event 'state:player' not received within 5s`

**Possible causes**:
1. Backend not broadcasting events
2. Client not subscribed to correct room
3. Timeout too short

**Debug**:
```python
# Check captured events
print(f"Captured events: {client.captured_events}")

# Increase timeout
event = await client.wait_for_event("state:player", timeout=10.0)

# Check room subscription
await client.join_room("playlists")
await asyncio.sleep(1.0)  # Allow subscription to complete
```

### Contract Validation Failure

**Error**: `AssertionError: Envelope validation failed`

**Debug**:
```python
# Disable auto-validation to inspect event
client = WebSocketTestClient(base_url=BACKEND_URL, auto_validate=False)

# Manually inspect event
event = await client.wait_for_event("state:player")
print(json.dumps(event.data, indent=2))

# Validate manually
validator.validate_event("state:player", event.data)
```

### server_seq Not Increasing

**Error**: `AssertionError: server_seq not monotonically increasing`

**Debug**:
```python
# Get all state events
state_events = client.get_events("state:player")

# Check sequences
seqs = [e.data["server_seq"] for e in state_events]
print(f"Sequences: {seqs}")

# This may indicate a backend bug
```

## Best Practices

### 1. Always Subscribe First

```python
# Good
await client.join_room("playlists")
await asyncio.sleep(0.5)  # Allow subscription
response = await http_client.post("/api/player/toggle")
event = await client.wait_for_event("state:player")

# Bad - may miss event
response = await http_client.post("/api/player/toggle")
await client.join_room("playlists")  # Too late!
```

### 2. Clear Events Between Tests

```python
@pytest.mark.asyncio
async def test_something(websocket_client):
    websocket_client.clear_events()  # Start fresh
    # ... test code ...
```

### 3. Use Predicates for Specific Events

```python
# Wait for event with specific playlist_id
event = await client.wait_for_event(
    "state:playlist",
    predicate=lambda e: e.data.get("playlist_id") == "my-playlist-id"
)
```

### 4. Clean Up Resources

```python
playlist_id = None
try:
    # Create test resource
    response = await http_client.post("/api/playlists", json={...})
    playlist_id = response.json()["data"]["id"]

    # ... test code ...

finally:
    # Always clean up
    if playlist_id:
        await http_client.delete(f"/api/playlists/{playlist_id}")
```

### 5. Test Multi-Client Scenarios

Always test that:
- Multiple clients receive same state
- Originating client also receives broadcast (server-authoritative)
- server_seq is identical across all clients

## Coverage

Current test coverage for WebSocket functionality:

- ✅ Player state broadcasts
- ✅ Volume changes
- ✅ Seek position updates
- ✅ Playlist CRUD operations
- ✅ Track reordering
- ✅ Multi-client synchronization
- ✅ server_seq monotonicity
- ✅ Contract validation
- ✅ Disconnect/reconnect scenarios
- ⏳ NFC events (TODO)
- ⏳ Upload events (TODO)
- ⏳ System events (TODO)

## Contributing

When adding new tests:

1. Follow existing naming conventions: `test_<feature>_<expected_behavior>`
2. Use type hints for all parameters
3. Add docstrings explaining the test flow
4. Clean up created resources in `finally` blocks
5. Ensure tests pass both individually and as a suite

## References

- [Socket.IO Contracts](../../../../../../contracts/schemas/socketio_contracts.json)
- [OpenAPI Contracts](../../../../../../contracts/schemas/openapi.yaml)
- [pytest-asyncio docs](https://pytest-asyncio.readthedocs.io/)
- [python-socketio client](https://python-socketio.readthedocs.io/en/latest/client.html)
