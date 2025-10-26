# Developer Guide - TheOpenMusicBox

**Purpose**: Practical guide for developers working on TheOpenMusicBox codebase
**Audience**: Backend and Full-Stack developers
**Last Updated**: 2025-10-06

---

## Table of Contents

1. [Dependency Injection Container](#dependency-injection-container)
2. [Type Safety Best Practices](#type-safety-best-practices)
3. [Error Handling Patterns](#error-handling-patterns)
4. [Testing Guidelines](#testing-guidelines)
5. [Code Style & Conventions](#code-style--conventions)

---

## Dependency Injection Container

### Overview

TheOpenMusicBox uses a professional DI container for service lifecycle management. Services are created once (singleton) and automatically resolved with their dependencies.

### Container Architecture

```python
ApplicationContainer
├── Infrastructure Container (base)
│   ├── Database Services
│   ├── Hardware Adapters
│   └── External APIs
│
├── Application Services (registered)
│   ├── DataApplicationService
│   ├── AudioApplicationService
│   ├── NfcApplicationService
│   └── UploadApplicationService
│
└── Domain Services (lazy loaded)
    ├── PlaylistService
    ├── TrackService
    └── AudioEngine
```

### Getting Services from Container

```python
from app.src.dependencies import get_application_container

# Get container instance
container = get_application_container()

# Get service (automatically resolves dependencies)
data_service = container.get("data_application_service")
audio_service = container.get("audio_application_service")
```

### Registering New Services

**Step 1: Define your service**

```python
# app/src/application/services/my_service.py
from app.src.domain.protocols import SomeProtocol

class MyApplicationService:
    """New application service."""

    def __init__(
        self,
        dependency_a: SomeProtocol,
        dependency_b: AnotherService
    ):
        self._dep_a = dependency_a
        self._dep_b = dependency_b

    async def do_something(self) -> None:
        """Use case implementation."""
        # Your logic here
```

**Step 2: Register in container**

```python
# app/src/application/di/application_container.py
class ApplicationContainer(InfrastructureContainer):
    def __init__(self):
        super().__init__()
        self._register_application_services()

    def _register_application_services(self):
        # Other services...

        # Register your service
        self.register(
            "my_application_service",
            lambda: MyApplicationService(
                dependency_a=self.get("some_protocol_impl"),
                dependency_b=self.get("another_service")
            ),
            singleton=True
        )
```

**Step 3: Use in routes**

```python
# app/src/api/endpoints/my_api_routes.py
class MyAPIRoutes:
    def __init__(self, my_service: MyApplicationService):
        self.router = APIRouter(prefix="/api/my-feature")
        self._my_service = my_service
        self._register_routes()
```

### Key Features

1. **Singleton Management**: Services created once, reused
2. **Factory Pattern**: Lazy initialization when needed
3. **Dependency Resolution**: Automatic dependency graph
4. **Lifecycle Hooks**: Startup/shutdown support
5. **Type Safety**: Generic type support

### Best Practices

✅ **DO**:
- Use DI for all application and infrastructure services
- Register services in the appropriate container layer
- Use lazy loading for expensive services
- Define clear interfaces/protocols

❌ **DON'T**:
- Create global instances (use deprecated globals are being phased out)
- Instantiate services directly in routes
- Circular dependencies (will cause initialization errors)
- Mix service creation with business logic

---

## Type Safety Best Practices

### Overview

TheOpenMusicBox uses comprehensive type safety across Python (type hints + Pydantic) and TypeScript.

### Python Type Hints

**All public methods must have type hints:**

```python
from typing import Optional, Dict, List, Any

async def create_playlist(
    self,
    name: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Create new playlist.

    Args:
        name: Playlist name (required)
        description: Optional description

    Returns:
        Dict containing playlist data

    Raises:
        ValidationError: If name is invalid
        DatabaseError: If creation fails
    """
    # Implementation
```

### Pydantic Models for Validation

**Use Pydantic for all API request/response models:**

```python
from pydantic import BaseModel, Field

class PlaylistCreateRequest(BaseModel):
    """Request model for playlist creation."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    client_op_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Playlist",
                "description": "My favorite songs"
            }
        }

class PlaylistResponse(BaseModel):
    """Response model for playlist."""

    id: int
    name: str
    description: Optional[str]
    track_count: int
    created_at: str
    updated_at: str
```

### Domain Value Objects

**Use value objects for domain concepts:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TagIdentifier:
    """NFC tag identifier value object."""
    uid: str

    def __post_init__(self):
        if not self.uid or len(self.uid) < 4:
            raise ValueError("Invalid tag UID")

    def __str__(self) -> str:
        return self.uid

@dataclass(frozen=True)
class Duration:
    """Audio duration value object."""
    seconds: float

    def to_milliseconds(self) -> int:
        return int(self.seconds * 1000)

    def to_human_readable(self) -> str:
        minutes = int(self.seconds // 60)
        secs = int(self.seconds % 60)
        return f"{minutes}:{secs:02d}"
```

### TypeScript Interfaces

**Frontend type definitions:**

```typescript
// src/types/playlist.ts
export interface Playlist {
  id: number
  name: string
  description?: string
  track_count: number
  created_at: string
  updated_at: string
}

export interface PlaylistCreateRequest {
  name: string
  description?: string
  client_op_id?: string
}

export interface PlaylistUpdateRequest {
  name?: string
  description?: string
  client_op_id?: string
}
```

### Benefits

- ✅ Compile-time error detection
- ✅ Better IDE support (autocomplete, refactoring)
- ✅ Self-documenting code
- ✅ Reduced runtime errors
- ✅ Contract validation (frontend-backend)

---

## Error Handling Patterns

### Overview

TheOpenMusicBox uses a unified error handling system with consistent error responses across all layers.

### Error Classification

```python
from app.src.infrastructure.error_handling.unified_error_handler import (
    UnifiedErrorHandler,
    DomainError,        # 400-level errors
    InfrastructureError # 500-level errors
)

# Domain errors (client fault)
raise DomainError("Playlist name is required", error_code="VALIDATION_ERROR")

# Infrastructure errors (server fault)
raise InfrastructureError("Database connection failed", error_code="DB_ERROR")
```

### Standard Error Response Format

All errors return this structure:

```json
{
  "status": "error",
  "error": {
    "type": "validation_error",
    "message": "Playlist name is required",
    "details": {
      "field": "name",
      "constraint": "min_length"
    },
    "client_op_id": "abc123",
    "timestamp": "2025-10-06T12:34:56Z"
  }
}
```

### Error Decorator Pattern

**Use decorators for automatic error handling:**

```python
from app.src.services.error.unified_error_decorator import handle_service_errors

@handle_service_errors("playlist_service")
async def create_playlist(self, name: str) -> Dict:
    """Create playlist.

    Errors are automatically:
    - Caught and logged
    - Formatted to standard response
    - Broadcast to clients if needed
    """
    if not name:
        raise DomainError("Name is required", error_code="VALIDATION_ERROR")

    try:
        playlist = await self._repository.create(name)
        return playlist.to_dict()
    except DatabaseError as e:
        raise InfrastructureError(
            "Failed to create playlist",
            error_code="DB_CREATE_ERROR",
            original_error=e
        )
```

### Logging Best Practices

**Structured logging with context:**

```python
import logging

logger = logging.getLogger(__name__)

# Log with context for debugging
logger.info(
    "Playlist created",
    extra={
        "playlist_id": playlist.id,
        "user_id": user_id,
        "client_op_id": client_op_id,
        "action": "playlist_create"
    }
)

# Error logging with exception
try:
    result = await dangerous_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        exc_info=True,  # Include stack trace
        extra={
            "operation": "dangerous_operation",
            "params": {"param1": value1}
        }
    )
    raise
```

### Error Handling in Routes

**Handle errors at route level:**

```python
from fastapi import HTTPException, status

@router.post("/playlists")
async def create_playlist(request: PlaylistCreateRequest):
    try:
        # Delegate to service
        result = await playlist_service.create_playlist(
            name=request.name,
            description=request.description
        )
        return UnifiedResponseService.success(result)

    except DomainError as e:
        # Client error (400-level)
        return UnifiedResponseService.error(
            message=str(e),
            error_type=e.error_code,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    except InfrastructureError as e:
        # Server error (500-level)
        logger.error("Infrastructure error", exc_info=True)
        return UnifiedResponseService.error(
            message="Internal server error",
            error_type="INTERNAL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### Frontend Error Handling

**Consistent error handling on client:**

```typescript
// src/services/apiService.ts
async function createPlaylist(data: PlaylistCreateRequest): Promise<Playlist> {
  try {
    const response = await apiClient.post('/api/playlists', data)

    if (response.data.status === 'error') {
      throw new ApiError(
        response.data.error.message,
        response.data.error.type,
        response.data.error.details
      )
    }

    return response.data.data
  } catch (error) {
    // Network error
    if (!error.response) {
      throw new NetworkError('Network request failed')
    }
    // Re-throw API errors
    throw error
  }
}
```

---

## Testing Guidelines

### Test Structure

Follow the test pyramid:

```
E2E Tests (Frontend)
├── User Journey Tests
├── Cross-Browser Tests
└── Accessibility Tests

Integration Tests (Backend)
├── NFC Workflow E2E
├── Upload Integration
└── State Broadcasting

Contract Tests
├── Backend Contracts (76)
└── Frontend Contracts (76)

Unit Tests
├── Domain Layer (499 tests)
├── Application Layer (284 tests)
├── API Layer (287 tests)
└── Infrastructure Layer (144 tests)
```

### Writing Unit Tests

```python
# tests/unit/domain/data/test_playlist_service.py
import pytest
from unittest.mock import Mock, AsyncMock

class TestPlaylistService:
    """Unit tests for PlaylistService."""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing."""
        return Mock(spec=PlaylistRepositoryInterface)

    @pytest.fixture
    def service(self, mock_repository):
        """Service instance with mocked dependencies."""
        return PlaylistService(repository=mock_repository)

    async def test_create_playlist_success(self, service, mock_repository):
        """Test successful playlist creation."""
        # Arrange
        mock_repository.create = AsyncMock(return_value=Playlist(
            id=1, name="Test", track_count=0
        ))

        # Act
        result = await service.create_playlist("Test")

        # Assert
        assert result.id == 1
        assert result.name == "Test"
        mock_repository.create.assert_called_once()
```

### Contract Testing

See [Contract Testing Framework](../back/tests/contracts/CONTRACT_TEST_PROGRESS.md) for complete guide.

---

## Code Style & Conventions

### Python Style

- **PEP 8** compliance
- **Type hints** on all public methods
- **Docstrings** for all classes and public methods
- **120 character** line limit
- **Absolute imports** preferred

### Naming Conventions

```python
# Classes: PascalCase
class PlaylistService:
    pass

# Functions/methods: snake_case
def create_playlist(name: str) -> Playlist:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_PLAYLIST_NAME_LENGTH = 255

# Private methods: _prefixed_snake_case
def _validate_name(self, name: str) -> bool:
    pass
```

### TypeScript Style

- **ESLint** configuration
- **Interface** for types (not type alias for objects)
- **PascalCase** for types/interfaces
- **camelCase** for variables/functions
- **Explicit return types** on functions

### Architecture Layers

**Respect dependency direction:**

```
Presentation (Routes)
    ↓ depends on
Application (Use Cases)
    ↓ depends on
Domain (Business Logic)
    ↑ implemented by
Infrastructure (Adapters)
```

**Never import:**
- ❌ Domain → Infrastructure
- ❌ Domain → Application
- ❌ Application → Presentation

### Git Commit Convention

```bash
# Format: <type>(<scope>): <subject>

feat(playlist): add bulk delete operation
fix(audio): resolve playback stuttering issue
refactor(di): improve container lifecycle management
docs(api): update endpoint documentation
test(domain): add playlist validation tests
```

---

## Additional Resources

- [Backend Services Architecture](./backend-services-architecture.md) - Service layer details
- [Routing Architecture](./routing-architecture.md) - Two-layer routing pattern
- [API & Socket.IO Communication](./api-socketio-communication.md) - Real-time patterns
- [Contract Testing](../back/tests/contracts/CONTRACT_TEST_PROGRESS.md) - Contract validation
- [Testing Patterns](../front/src/tests/patterns/TESTING_PATTERNS.md) - Frontend testing

---

**Contributing**: Follow these guidelines when contributing to TheOpenMusicBox. Quality and consistency are our priorities.
