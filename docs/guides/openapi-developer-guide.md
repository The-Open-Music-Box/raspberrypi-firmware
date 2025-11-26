# OpenAPI/Swagger Developer Guide

This guide explains how to use and enhance the OpenAPI/Swagger documentation in TheOpenMusicBox.

## Table of Contents

- [Overview](#overview)
- [Accessing Documentation](#accessing-documentation)
- [Configuration](#configuration)
- [Adding Response Examples](#adding-response-examples)
- [Customizing Endpoints](#customizing-endpoints)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

TheOpenMusicBox includes comprehensive OpenAPI (Swagger) documentation that provides:

- **Interactive API Explorer** (Swagger UI)
- **Professional Documentation** (ReDoc)
- **Machine-readable API Spec** (OpenAPI JSON/YAML)
- **Request/Response Examples**
- **Organized Tags and Categories**
- **Error Response Documentation**

### Technology Stack

- **FastAPI**: Built-in OpenAPI support
- **Swagger UI**: Interactive API testing
- **ReDoc**: Beautiful API documentation
- **Pydantic**: Automatic schema generation

## Accessing Documentation

### Local Development

When running the application locally:

```bash
# Swagger UI (interactive)
http://localhost:8000/docs

# ReDoc (clean documentation)
http://localhost:8000/redoc

# OpenAPI JSON schema
http://localhost:8000/openapi.json
```

### Raspberry Pi Deployment

```bash
# Swagger UI
http://raspberrypi.local:8000/docs

# ReDoc
http://raspberrypi.local:8000/redoc

# Or use IP address
http://192.168.1.100:8000/docs
```

## Configuration

### Main Configuration File

**Location**: `back/app/src/config/openapi_config.py`

This file contains:
- API metadata (title, version, description)
- Tag definitions with descriptions
- Server configurations
- Custom schema modifications

```python
from app.src.config.openapi_config import get_openapi_config

# Get configuration
config = get_openapi_config()
```

### API Metadata

Update API information in `openapi_config.py`:

```python
API_TITLE = "TheOpenMusicBox API"
API_VERSION = "3.0.0"
API_DESCRIPTION = """
Your comprehensive API description here...
"""

API_CONTACT = {
    "name": "Your Name",
    "email": "your.email@example.com",
}

API_LICENSE = {
    "name": "Non-Commercial License",
    "url": "https://github.com/yourusername/theopenmusicbox/blob/main/LICENSE",
}
```

### Tags Organization

Tags group related endpoints together:

```python
API_TAGS_METADATA = [
    {
        "name": "player",
        "description": "Player control operations with real-time updates"
    },
    {
        "name": "playlists",
        "description": "Playlist CRUD and management"
    },
    # ... more tags
]
```

## Adding Response Examples

### Step 1: Define Examples

**Location**: `back/app/src/config/openapi_examples.py`

Create reusable response examples:

```python
MY_CUSTOM_EXAMPLE = {
    "description": "Successful operation",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Operation completed",
                "data": {
                    "field1": "value1",
                    "field2": "value2"
                },
                "timestamp": 1704067200000,
                "server_seq": 12345
            }
        }
    }
}
```

### Step 2: Import Examples

In your API routes file:

```python
from app.src.config.openapi_examples import (
    PLAYER_STATUS_EXAMPLE,
    ERROR_404_EXAMPLE,
    ERROR_400_EXAMPLE
)
```

### Step 3: Apply to Endpoints

Use the `responses` parameter in route decorators:

```python
@self.router.get(
    "/status",
    summary="Get player status",
    description="Retrieve current playback status including track, position, and volume",
    responses={
        200: PLAYER_STATUS_EXAMPLE,
        404: ERROR_404_EXAMPLE,
        503: ERROR_503_EXAMPLE
    }
)
async def get_player_status():
    # ... implementation
    pass
```

### Step 4: Use Combined Response Sets

For common combinations:

```python
from app.src.config.openapi_examples import PLAYER_RESPONSES

@self.router.get(
    "/status",
    responses=PLAYER_RESPONSES  # Includes 200, 400, 404, 429, 503
)
async def get_player_status():
    pass
```

## Customizing Endpoints

### Basic Endpoint Documentation

```python
@self.router.post(
    "/play",
    summary="Start playback",
    description="Start or resume audio playback. Broadcasts state update via Socket.IO.",
    tags=["player"],  # Optional: override tag
    response_model=SuccessResponse[PlayerState],
    responses={200: PLAYER_PLAY_EXAMPLE}
)
async def play_player(
    body: PlayerControlRequest = Body(
        ...,
        examples={
            "basic": {
                "summary": "Basic play request",
                "value": {"client_op_id": "op_123"}
            }
        }
    )
):
    pass
```

### Request Body Examples

Add examples to request models:

```python
from pydantic import Field

class VolumeRequest(ClientOperationRequest):
    """Request model for volume operations."""

    volume: int = Field(
        ...,
        ge=0,
        le=100,
        description="Volume level (0-100)",
        examples=[50, 75, 100]
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "volume": 75,
                    "client_op_id": "op_vol_001"
                },
                {
                    "volume": 50,
                    "client_op_id": "op_vol_002"
                }
            ]
        }
```

### Response Models

Define explicit response models for better documentation:

```python
from pydantic import BaseModel
from typing import Optional

class PlayerStatusData(BaseModel):
    """Player status data model."""
    is_playing: bool
    current_track: Optional[dict]
    position_ms: int
    volume: int
    playlist_id: Optional[str]

@self.router.get(
    "/status",
    response_model=SuccessResponse[PlayerStatusData],
    summary="Get player status"
)
async def get_status():
    pass
```

### Deprecation Notices

Mark deprecated endpoints:

```python
@self.router.get(
    "/old-endpoint",
    deprecated=True,
    summary="Old endpoint (deprecated)",
    description="This endpoint is deprecated. Use `/new-endpoint` instead."
)
async def old_endpoint():
    pass
```

## Best Practices

### 1. Always Add Descriptions

```python
@self.router.post(
    "/playlists",
    summary="Create playlist",  # Short summary (appears in list)
    description="""
    Create a new playlist with optional initial tracks.

    This endpoint:
    - Validates playlist name uniqueness
    - Creates filesystem directory
    - Broadcasts creation event via Socket.IO
    - Returns complete playlist object
    """,  # Detailed description (appears in docs)
)
async def create_playlist():
    pass
```

### 2. Document All Parameters

```python
async def get_playlists(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    pass
```

### 3. Include Response Examples

```python
responses={
    200: SUCCESS_EXAMPLE,
    400: VALIDATION_ERROR_EXAMPLE,
    404: NOT_FOUND_EXAMPLE,
    503: SERVICE_UNAVAILABLE_EXAMPLE
}
```

### 4. Use Proper HTTP Status Codes

```python
# Return appropriate status codes
return JSONResponse(
    status_code=201,  # Created
    content={"status": "success", ...}
)

return JSONResponse(
    status_code=204  # No Content (for deletes)
)
```

### 5. Group Related Endpoints

Use consistent tags:

```python
# All player endpoints
tags=["player"]

# All playlist endpoints
tags=["playlists"]
```

### 6. Document WebSocket Events

Add OpenAPI documentation for Socket.IO events in tag descriptions:

```python
{
    "name": "websocket",
    "description": """
    **WebSocket Events**

    Real-time updates via Socket.IO:
    - `state:player` - Player state changes
    - `state:playlists` - Playlist updates
    - `state:track_position` - Position updates (500ms)
    """
}
```

## Advanced Customization

### Custom OpenAPI Schema

Edit `customize_openapi_schema()` in `openapi_config.py`:

```python
def customize_openapi_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    # Add custom servers
    schema["servers"] = [
        {
            "url": "https://api.myapp.com",
            "description": "Production server"
        }
    ]

    # Add security schemes
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }

    # Add custom extensions
    schema["info"]["x-custom-field"] = "custom value"

    return schema
```

### Adding Security to Endpoints

```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@self.router.get(
    "/protected",
    dependencies=[Security(api_key_header)]
)
async def protected_endpoint():
    pass
```

## Troubleshooting

### Documentation Not Updating

1. **Clear Browser Cache**: Hard refresh (Ctrl+F5 / Cmd+Shift+R)
2. **Restart Server**: Changes to `openapi_config.py` require restart
3. **Check Imports**: Ensure examples are imported correctly

### Examples Not Showing

```python
# ❌ Wrong
responses={200: {"example": {...}}}

# ✅ Correct
responses={200: {
    "description": "Success",
    "content": {
        "application/json": {
            "example": {...}
        }
    }
}}
```

### Schema Errors

```python
# Ensure response models are valid Pydantic models
from pydantic import BaseModel

class MyResponse(BaseModel):
    field: str

# Use in response_model
@router.get("/", response_model=MyResponse)
```

### Tag Not Showing

Ensure tag is defined in `API_TAGS_METADATA`:

```python
API_TAGS_METADATA = [
    {
        "name": "my_tag",
        "description": "My tag description"
    }
]
```

## Testing Documentation

### Manual Testing

1. **Visit Swagger UI**: `http://localhost:8000/docs`
2. **Check Each Endpoint**: Verify examples appear
3. **Try It Out**: Use the interactive tester
4. **Check ReDoc**: `http://localhost:8000/redoc`

### Automated Testing

```python
# Test OpenAPI schema generation
def test_openapi_schema():
    from fastapi.testclient import TestClient
    from app.main import _fastapi_app

    client = TestClient(_fastapi_app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    # Verify metadata
    assert schema["info"]["title"] == "TheOpenMusicBox API"
    assert schema["info"]["version"] == "3.0.0"

    # Verify tags
    tag_names = [tag["name"] for tag in schema["info"]["tags"]]
    assert "player" in tag_names
    assert "playlists" in tag_names
```

## Examples

### Complete Endpoint Example

```python
from fastapi import APIRouter, Body, Query
from app.src.config.openapi_examples import (
    PLAYLIST_DETAIL_EXAMPLE,
    ERROR_404_EXAMPLE
)

@self.router.get(
    "/playlists/{playlist_id}",
    summary="Get playlist by ID",
    description="""
    Retrieve a specific playlist with all tracks and metadata.

    **Returns**:
    - Playlist object with tracks array
    - NFC tag association (if exists)
    - Total duration and track count

    **WebSocket**: Clients in `playlist:{id}` room receive updates
    """,
    response_model=SuccessResponse[PlaylistData],
    responses={
        200: PLAYLIST_DETAIL_EXAMPLE,
        404: ERROR_404_EXAMPLE
    },
    tags=["playlists"]
)
async def get_playlist(
    playlist_id: str = Path(..., description="Unique playlist identifier")
):
    # Implementation
    pass
```

### Request Body with Examples

```python
from pydantic import BaseModel, Field

class CreatePlaylistRequest(BaseModel):
    """Request to create a new playlist."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Playlist name",
        examples=["My Favorites", "Workout Mix", "Chill Vibes"]
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "name": "My Favorites",
                    "client_op_id": "create_playlist_001"
                },
                {
                    "name": "Workout Mix",
                    "client_op_id": "create_playlist_002"
                }
            ]
        }
```

## Resources

- **FastAPI OpenAPI Docs**: https://fastapi.tiangolo.com/tutorial/metadata/
- **OpenAPI Specification**: https://swagger.io/specification/
- **ReDoc Documentation**: https://github.com/Redocly/redoc
- **Swagger UI**: https://swagger.io/tools/swagger-ui/

## Summary

OpenAPI/Swagger integration provides:

✅ **Interactive API Testing** via Swagger UI
✅ **Professional Documentation** via ReDoc
✅ **Code Examples** for all endpoints
✅ **Type Safety** via Pydantic models
✅ **Automatic Schema Generation**
✅ **Developer-Friendly** documentation

For questions or contributions, see the main repository documentation.
