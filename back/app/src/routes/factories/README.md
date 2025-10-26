# Bootstrap Routes (Layer 2)

## Purpose

This directory contains **Bootstrap/Factory route classes** - the second layer of TheOpenMusicBox's two-layer routing architecture. These classes are responsible for **dependency injection, service initialization, and route registration**, without handling HTTP request/response logic.

## Responsibilities

✅ **What Bootstrap Routes DO**:
- Import and instantiate API route classes from `back/app/src/api/endpoints/`
- Create and configure required application services
- Initialize infrastructure components (StateManager, broadcasting services, etc.)
- Configure dependency injection (often using getter functions)
- Register routes with the FastAPI application
- Manage service lifecycle (startup/shutdown/cleanup)
- Coordinate between multiple services and components

❌ **What Bootstrap Routes DON'T DO**:
- Define route endpoints or HTTP handlers
- Process HTTP requests or responses
- Perform input validation or response formatting
- Implement business logic

## Architecture Pattern

Bootstrap Routes follow the **Factory Pattern** and **Dependency Injection** principles:

```python
# Bootstrap Route (Layer 2)
from app.src.api.endpoints.player_api_routes import PlayerAPIRoutes

class PlayerRoutesDDD:
    """
    Bootstrap class for player routes.

    Responsibilities:
    - Initialize DDD components with proper dependencies
    - Register API routes with FastAPI
    - Coordinate service dependencies
    - Manage player operations lifecycle
    """

    def __init__(self, app: FastAPI, socketio: AsyncServer, playback_coordinator, config=None):
        self.app = app
        self.socketio = socketio
        self.playback_coordinator = playback_coordinator

        # Step 1: Initialize core services
        self.state_manager = UnifiedStateManager(self.socketio)

        # Step 2: Initialize application services
        self.player_application_service = PlayerApplicationService(
            self.playback_coordinator,
            self.state_manager
        )

        # Step 3: Initialize API-layer services
        self.broadcasting_service = PlayerBroadcastingService(self.state_manager)
        self.operations_service = PlayerOperationsService(self.player_application_service)

        # Step 4: Initialize API routes with all dependencies
        self.api_routes = PlayerAPIRoutes(
            player_service=self.player_application_service,
            broadcasting_service=self.broadcasting_service,
            operations_service=self.operations_service
        )

        # Step 5: Register routes with FastAPI
        self.app.include_router(self.api_routes.get_router())

        logger.info("✅ Player routes initialized and registered")
```

## File Structure

| File | Bootstrap Class | API Routes Class | Purpose |
|------|----------------|------------------|---------|
| `player_routes_ddd.py` | `PlayerRoutesDDD` | `PlayerAPIRoutes` | Player control routes |
| `playlist_routes_ddd.py` | `PlaylistRoutesDDD` | `PlaylistAPIRoutes` | Playlist management routes |
| `nfc_unified_routes.py` | `UnifiedNFCRoutes` | `NFCAPIRoutes` | NFC integration routes |
| `system_routes.py` | `SystemRoutes` | `SystemAPIRoutes` | System status routes |
| `upload_routes.py` | `UploadRoutes` | `UploadAPIRoutes` | Upload session routes |
| `youtube_routes.py` | `YouTubeRoutes` | `YouTubeAPIRoutes` | YouTube download routes |
| `web_routes.py` | `WebRoutes` | `WebAPIRoutes` | Static web routes |

## Relationship with API Routes

Bootstrap Routes **import and initialize** API Routes:

```
This directory (back/app/src/routes/factories/)
    ↓ imports
back/app/src/api/endpoints/ (API Routes)
    ↓ uses
Application Services
    ↓ uses
Domain Layer
```

## Key Design Patterns

### 1. Factory Pattern

Bootstrap routes act as factories that create and configure route handlers:

```python
class SystemRoutes:
    def __init__(self, app: FastAPI):
        self.app = app
        self.api_routes = None

    def initialize(self):
        """Factory method to create API routes with dependencies."""
        # Create dependency getter
        def get_playback_coordinator(request):
            from app.src.dependencies import get_playback_coordinator as get_coord
            return get_coord()

        # Create API routes with dependencies
        self.api_routes = SystemAPIRoutes(
            playback_coordinator_getter=get_playback_coordinator
        )

    def register(self):
        """Register routes with FastAPI."""
        if not self.api_routes:
            self.initialize()
        self.app.include_router(self.api_routes.get_router())
```

### 2. Dependency Injection via Getter Functions

Many bootstrap routes use getter functions for lazy dependency resolution:

```python
def get_nfc_service(request):
    """Get NFC service from domain application."""
    application = getattr(request.app, "application", None)
    if not application:
        raise service_unavailable_error("Domain application not available")

    nfc_service = getattr(application, "_nfc_app_service", None)
    if not nfc_service:
        raise service_unavailable_error("NFC service not available")

    return nfc_service

# Pass getter to API routes
self.api_routes = NFCAPIRoutes(
    nfc_service_getter=get_nfc_service,
    state_manager_getter=get_state_manager
)
```

**Why getter functions?**
- Lazy resolution: Service fetched when needed, not at initialization
- Avoids circular dependencies
- Handles missing services gracefully
- Request-scoped dependencies

### 3. State Manager Integration

Most bootstrap routes initialize the `UnifiedStateManager` for real-time broadcasting:

```python
# Initialize state management
self.state_manager = UnifiedStateManager(self.socketio)

# Use state manager for broadcasting
self.broadcasting_service = PlaylistBroadcastingService(self.state_manager)
```

### 4. Lifecycle Management

Bootstrap routes can provide cleanup methods:

```python
async def cleanup(self):
    """Clean up resources when shutting down."""
    try:
        logger.info("🧹 Cleaning up playlist routes resources")
        if hasattr(self, "cleanup_background_tasks"):
            await self.cleanup_background_tasks()
        logger.info("✅ Playlist routes cleanup completed")
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}")
```

## Initialization Flow

### 1. Main Entry Point

`main.py` → `api_routes_state.py` orchestrates all bootstrap routes:

```python
# back/app/src/routes/factories/api_routes_state.py
class APIRoutesState:
    def __init__(self, app: FastAPI, socketio, config=None):
        self.app = app
        self.socketio = socketio

        # Initialize all bootstrap routes
        self.playlist_routes = PlaylistRoutesDDD(app, socketio, config)
        self.player_routes = PlayerRoutesDDD(app, socketio, playback_coordinator, config)
        self.nfc_routes = UnifiedNFCRoutes(app, socketio)
        self.youtube_routes = YouTubeRoutes(app, socketio)
        self.upload_routes = UploadRoutes(app, socketio)
        self.system_routes = SystemRoutes(app)
        self.web_routes = WebRoutes(app)

    def init_routes(self):
        """Register all routes with FastAPI."""
        self.playlist_routes.register()
        self.nfc_routes.register_with_app()
        self.youtube_routes.register()
        self.upload_routes.register_with_app()
        self.system_routes.register()
        self.web_routes.register()
```

### 2. Dependency Tree

Each bootstrap route builds a dependency tree:

```
PlayerRoutesDDD
├── UnifiedStateManager (socketio)
├── PlayerApplicationService
│   ├── PlaybackCoordinator
│   └── StateManager
├── PlayerBroadcastingService
│   └── StateManager
├── PlayerOperationsService
│   └── PlayerApplicationService
└── PlayerAPIRoutes (imports from api/endpoints/)
    ├── PlayerApplicationService
    ├── PlayerBroadcastingService
    └── PlayerOperationsService
```

## Common Patterns

### Pattern 1: Simple Bootstrap

Minimal bootstrap with getter functions:

```python
class UploadRoutes:
    def __init__(self, app: FastAPI, socketio: AsyncServer):
        self.app = app
        self.socketio = socketio
        self.api_routes = None

    def initialize(self):
        def get_upload_controller(request):
            playlist_routes_ddd = getattr(request.app, "playlist_routes_ddd", None)
            if playlist_routes_ddd:
                return playlist_routes_ddd.upload_controller
            return None

        self.api_routes = UploadAPIRoutes(upload_controller_getter=get_upload_controller)

    def register_with_app(self, prefix: str = "/api/uploads"):
        if not self.api_routes:
            self.initialize()
        self.app.include_router(self.api_routes.get_router(), prefix=prefix, tags=["uploads"])
```

### Pattern 2: DDD Bootstrap with Services

Full DDD initialization with multiple services:

```python
class PlaylistRoutesDDD:
    def __init__(self, app: FastAPI, socketio: AsyncServer, config=None):
        self.app = app
        self.socketio = socketio

        # Core services
        self.state_manager = UnifiedStateManager(self.socketio)
        self.websocket_handlers = WebSocketStateHandlers(self.socketio, self.app, self.state_manager)

        # Application services
        playlist_app_service = get_data_application_service()
        self.broadcasting_service = PlaylistBroadcastingService(self.state_manager)
        self.operations_service = PlaylistOperationsService(playlist_app_service)

        # API routes
        self.api_routes = PlaylistAPIRoutes(
            playlist_service=playlist_app_service,
            broadcasting_service=self.broadcasting_service,
            operations_service=self.operations_service
        )

        # Register routes
        self.app.include_router(self.api_routes.get_router())
```

### Pattern 3: Socket.IO Configuration

Configure Socket.IO for services that need it:

```python
class UnifiedNFCRoutes:
    def __init__(self, app: FastAPI, socketio: AsyncServer):
        self.app = app
        self.socketio = socketio
        self._configure_nfc_socketio()

    def _configure_nfc_socketio(self):
        """Configure Socket.IO for the NFC service."""
        application = getattr(self.app, "application", None)
        if application:
            nfc_service = getattr(application, "_nfc_app_service", None)
            if nfc_service and hasattr(nfc_service, "set_socketio"):
                nfc_service.set_socketio(self.socketio)
                logger.info("✅ Socket.IO configured for NFC service")
```

## Best Practices

### ✅ DO:
- Initialize all required services in the constructor
- Use getter functions for lazy/request-scoped dependencies
- Provide cleanup methods for resource management
- Document all dependencies and their purposes
- Follow consistent naming (`*Routes`, `*RoutesDDD`)
- Register routes in a dedicated method (`.register()`, `.register_with_app()`)

### ❌ DON'T:
- Define route handlers in bootstrap routes
- Handle HTTP request/response logic
- Implement business logic
- Access services without proper error handling
- Create circular dependencies

## Adding New Bootstrap Routes

When adding new bootstrap routes:

1. **Create the bootstrap class**:
   ```python
   class NewFeatureRoutes:
       def __init__(self, app: FastAPI, socketio: AsyncServer):
           self.app = app
           self.socketio = socketio
   ```

2. **Initialize services**:
   ```python
   def initialize(self):
       # Initialize state manager
       self.state_manager = UnifiedStateManager(self.socketio)

       # Initialize application service
       self.feature_service = get_feature_application_service()

       # Initialize broadcasting
       self.broadcasting_service = FeatureBroadcastingService(self.state_manager)

       # Initialize API routes
       self.api_routes = NewFeatureAPIRoutes(
           feature_service=self.feature_service,
           broadcasting_service=self.broadcasting_service
       )
   ```

3. **Register routes**:
   ```python
   def register_with_app(self):
       if not self.api_routes:
           self.initialize()
       self.app.include_router(self.api_routes.get_router())
   ```

4. **Add to api_routes_state.py**:
   ```python
   class APIRoutesState:
       def __init__(self, app, socketio, config):
           # ... other routes ...
           self.new_feature_routes = NewFeatureRoutes(app, socketio)

       def init_routes(self):
           # ... other registrations ...
           self.new_feature_routes.register_with_app()
   ```

## Naming Conventions

Different naming patterns used in this directory:

- **`*RoutesDDD`** - Routes following full DDD pattern (e.g., `PlayerRoutesDDD`)
- **`Unified*Routes`** - Unified/combined route implementations (e.g., `UnifiedNFCRoutes`)
- **`*Routes`** - Simple bootstrap routes (e.g., `SystemRoutes`, `UploadRoutes`)

All serve the same purpose: dependency wiring and route registration.

## Testing Bootstrap Routes

Bootstrap routes should be tested for correct dependency wiring:

```python
def test_player_routes_initialization():
    # Mock dependencies
    mock_app = Mock(spec=FastAPI)
    mock_socketio = Mock(spec=AsyncServer)
    mock_coordinator = Mock()

    # Initialize bootstrap
    routes = PlayerRoutesDDD(mock_app, mock_socketio, mock_coordinator)

    # Verify services initialized
    assert routes.state_manager is not None
    assert routes.player_application_service is not None
    assert routes.broadcasting_service is not None
    assert routes.api_routes is not None

    # Verify routes registered
    mock_app.include_router.assert_called_once()
```

## Troubleshooting

### Service Not Available Error

**Problem**: Routes return 503 Service Unavailable

**Solution**:
1. Check bootstrap route initializes the service
2. Verify getter function handles missing services
3. Ensure service is added to application context

### Routes Not Found (404)

**Problem**: Routes not accessible

**Solution**:
1. Verify bootstrap route calls `app.include_router()`
2. Check router prefix matches expected URL
3. Ensure bootstrap is registered in `api_routes_state.py`

### Circular Dependencies

**Problem**: Import errors or initialization failures

**Solution**:
- Use getter functions for lazy dependency resolution
- Review dependency graph
- Apply dependency inversion where needed

## Related Documentation

- **[API Routes README](../api/endpoints/README.md)** - Layer 1 documentation
- **[Routing Architecture](../../../documentation/routing-architecture.md)** - Complete two-layer explanation
- **[Backend Services Architecture](../../../documentation/backend-services-architecture.md)** - Overall DDD architecture
- **[Application Services](../application/README.md)** - Business logic layer

## Summary

Bootstrap Routes are the **dependency wiring and initialization layer** that:

✅ Create and configure services
✅ Initialize API routes with dependencies
✅ Register routes with FastAPI
✅ Manage service lifecycle
✅ Coordinate between components

They do **NOT** handle HTTP requests - that's the job of API Routes in `back/app/src/api/endpoints/`.

This separation provides:
- **Testability**: Test routing logic and dependency wiring separately
- **Flexibility**: Easy to modify dependencies without changing route logic
- **Maintainability**: Clear separation of concerns
- **Clean Architecture**: Proper dependency direction and layer isolation
