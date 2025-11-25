# API Routes (Layer 1)

## Purpose

This directory contains **pure API route handlers** - the first layer of TheOpenMusicBox's two-layer routing architecture. These classes define FastAPI route endpoints and handle HTTP request/response logic **without managing dependencies or service lifecycle**.

## Responsibilities

✅ **What API Routes DO**:
- Define FastAPI route endpoints using decorators (`@router.post()`, `@router.get()`, etc.)
- Handle HTTP request/response logic
- Perform input validation using Pydantic models
- Delegate business logic to application services (received via DI)
- Format and return standardized responses using `UnifiedResponseService`
- Handle route-specific error scenarios

❌ **What API Routes DON'T DO**:
- Instantiate services or dependencies
- Manage service lifecycle (startup/shutdown)
- Access global state or singletons directly
- Perform complex business logic (delegated to services)

## Architecture Pattern

These routes follow the **Dependency Injection** pattern - all dependencies are received via constructor parameters and stored as instance variables:

```python
class PlayerAPIRoutes:
    """Pure API routes handler for player operations."""

    def __init__(self, player_service, broadcasting_service, operations_service=None):
        self.router = APIRouter(prefix="/api/player", tags=["player"])
        self._player_service = player_service  # Injected dependency
        self._broadcasting_service = broadcasting_service  # Injected dependency
        self._operations_service = operations_service  # Optional dependency
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/play")
        async def play_player(body: PlayerControlRequest):
            # Delegate to injected service - no instantiation here
            result = await self._player_service.play_use_case()

            if result.get("success"):
                status = result.get("status", {})
                await self._broadcasting_service.broadcast_playback_state_changed(
                    "playing", status
                )
                return UnifiedResponseService.success(
                    message="Playback started successfully",
                    data=status
                )

    def get_router(self) -> APIRouter:
        """Return the configured FastAPI router."""
        return self.router
```

## File Structure

| File | Class | Endpoints | Purpose |
|------|-------|-----------|---------|
| `player_api_routes.py` | `PlayerAPIRoutes` | `/api/player/*` | Player control (play, pause, seek, volume) |
| `playlist_api_routes.py` | `PlaylistAPIRoutes` | `/api/playlists/*` | Playlist CRUD and management |
| `nfc_api_routes.py` | `NFCAPIRoutes` | `/api/nfc/*` | NFC tag association and scanning |
| `system_api_routes.py` | `SystemAPIRoutes` | `/api/playback/status`, `/api/health` | System health and status |
| `upload_api_routes.py` | `UploadAPIRoutes` | `/api/uploads/*` | File upload session management |
| `youtube_api_routes.py` | `YouTubeAPIRoutes` | `/api/youtube/*` | YouTube download integration |
| `web_api_routes.py` | `WebAPIRoutes` | Static file serving | Web UI assets |

## Relationship with Bootstrap Routes

API Routes in this directory are **imported and initialized** by Bootstrap Routes in `back/app/src/routes/factories/`:

```
back/app/src/routes/factories/player_routes_ddd.py (Bootstrap)
    ↓ imports & initializes
back/app/src/api/endpoints/player_api_routes.py (This directory)
```

The Bootstrap Routes:
1. Create and configure all required services
2. Instantiate the API Routes class with dependencies
3. Register the router with FastAPI

## Key Design Principles

### 1. Pure Functions (Route Handlers)
Route handler functions should be as pure as possible - they receive input, delegate to services, and return output:

```python
@self.router.post("/volume")
async def set_volume(body: VolumeRequest):
    # Pure flow: input → service → response
    result = await self._player_service.set_volume_use_case(body.volume)

    if result.get("success"):
        await self._broadcasting_service.broadcast_volume_changed(body.volume)
        status_result = await self._player_service.get_status_use_case()
        status = status_result.get("status", {})

        return UnifiedResponseService.success(
            message=f"Volume set to {body.volume}%",
            data={"volume": body.volume, **status}
        )
```

### 2. Standardized Responses
All routes use `UnifiedResponseService` for consistent response formatting:

```python
# Success response
return UnifiedResponseService.success(
    message="Operation successful",
    data=result_data,
    server_seq=status.get("server_seq"),
    client_op_id=body.client_op_id
)

# Error response
return UnifiedResponseService.error(
    message="Operation failed",
    error_type="validation_error",
    status_code=400
)
```

### 3. Request Models
Use Pydantic models for request validation:

```python
class VolumeRequest(ClientOperationRequest):
    """Request model for volume operations."""
    volume: int = Field(..., ge=0, le=100, description="Volume level (0-100)")
```

### 4. Error Handling
Use decorators for consistent error handling:

```python
@self.router.post("/play")
@handle_http_errors()
async def play_player(body: PlayerControlRequest):
    # Decorator handles exceptions and formats error responses
    ...
```

## Testing

API Routes are designed to be easily testable with mocked dependencies:

```python
# Test example
def test_play_endpoint():
    # Mock dependencies
    mock_player_service = Mock()
    mock_broadcasting_service = Mock()

    # Create API routes with mocks
    routes = PlayerAPIRoutes(
        player_service=mock_player_service,
        broadcasting_service=mock_broadcasting_service
    )

    # Test route handler logic
    ...
```

## Best Practices

### ✅ DO:
- Keep route handlers focused on HTTP concerns
- Delegate all business logic to services
- Use dependency injection for all services
- Return standardized responses
- Document all endpoints with docstrings
- Validate input using Pydantic models

### ❌ DON'T:
- Instantiate services inside route handlers
- Access global state or singletons
- Implement business logic in routes
- Handle service lifecycle in API routes
- Create side effects outside of service delegation

## Adding New Routes

When adding new routes to this directory:

1. **Create the API Routes class**:
   ```python
   class NewFeatureAPIRoutes:
       def __init__(self, feature_service, broadcasting_service):
           self.router = APIRouter(prefix="/api/feature", tags=["feature"])
           self._feature_service = feature_service
           self._broadcasting_service = broadcasting_service
           self._register_routes()
   ```

2. **Define route handlers**:
   ```python
   def _register_routes(self):
       @self.router.post("/action")
       @handle_http_errors()
       async def perform_action(body: ActionRequest):
           result = await self._feature_service.action_use_case(...)
           return UnifiedResponseService.success(...)
   ```

3. **Create corresponding Bootstrap Route** in `back/app/src/routes/factories/`:
   ```python
   class NewFeatureRoutes:
       def __init__(self, app: FastAPI, socketio: AsyncServer):
           # Initialize services
           self.feature_service = FeatureApplicationService(...)
           self.broadcasting_service = FeatureBroadcastingService(...)

           # Initialize API routes
           self.api_routes = NewFeatureAPIRoutes(
               feature_service=self.feature_service,
               broadcasting_service=self.broadcasting_service
           )

           # Register routes
           app.include_router(self.api_routes.get_router())
   ```

4. **Register in api_routes_state.py**:
   ```python
   self.new_feature_routes = NewFeatureRoutes(app, socketio)
   ```

## Related Documentation

- **[Routing Architecture](../../../../documentation/routing-architecture.md)** - Complete two-layer routing explanation
- **[Backend Services Architecture](../../../../documentation/backend-services-architecture.md)** - Overall DDD architecture
- **[Bootstrap Routes README](../../routes/factories/README.md)** - Layer 2 documentation
- **[Application Services](../../application/README.md)** - Business logic layer

## Questions?

If you're unsure about:
- **Where to put business logic**: Use Application Services, not API routes
- **How to access dependencies**: Receive via constructor injection
- **How to test routes**: Mock dependencies and test the route handler
- **Where to manage lifecycle**: Use Bootstrap Routes in `back/app/src/routes/factories/`

See the [Routing Architecture documentation](../../../../documentation/routing-architecture.md) for comprehensive guidance.
