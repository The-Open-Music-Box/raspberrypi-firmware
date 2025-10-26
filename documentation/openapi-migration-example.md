# OpenAPI Enhancement Migration Example

This document shows how to enhance existing API endpoints with comprehensive OpenAPI documentation.

## Before: Basic Endpoint

```python
# back/app/src/api/endpoints/player_api_routes.py
@self.router.get("/status")
async def get_player_status(request: Request):
    """Get player status."""
    result = await self._player_service.get_status_use_case()
    return UnifiedResponseService.success(
        message="Player status retrieved",
        data=result.get("status", {})
    )
```

**Problems**:
- ❌ No request/response examples
- ❌ No detailed description
- ❌ No documented error responses
- ❌ No response model

## After: Enhanced Endpoint

```python
# back/app/src/api/endpoints/player_api_routes.py
from app.src.config.openapi_examples import (
    PLAYER_STATUS_EXAMPLE,
    ERROR_404_EXAMPLE,
    ERROR_503_EXAMPLE
)
from app.src.common.response_models import SuccessResponse
from pydantic import BaseModel

# Define response data model
class PlayerStatusData(BaseModel):
    """Player status response data."""
    is_playing: bool
    current_track: Optional[dict]
    position_ms: int
    volume: int
    playlist_id: Optional[str]

@self.router.get(
    "/status",
    summary="Get current player status",
    description="""
    Retrieve the current playback status including:
    - Playing state (playing/paused/stopped)
    - Current track information
    - Playback position in milliseconds
    - Volume level (0-100)
    - Associated playlist (if any)

    **Real-time Updates**: Clients subscribed to the 'playlists' room
    receive `state:player` events when playback status changes.

    **Caching**: This endpoint includes cache-busting headers to ensure
    fresh data on page refresh.
    """,
    response_model=SuccessResponse[PlayerStatusData],
    responses={
        200: PLAYER_STATUS_EXAMPLE,
        404: ERROR_404_EXAMPLE,
        503: ERROR_503_EXAMPLE
    },
    tags=["player"]
)
async def get_player_status(request: Request):
    """Get player status with comprehensive error handling."""
    result = await self._player_service.get_status_use_case()
    return UnifiedResponseService.success(
        message="Player status retrieved successfully",
        data=result.get("status", {}),
        server_seq=result.get("server_seq")
    )
```

**Improvements**:
- ✅ Detailed description with formatting
- ✅ Response examples for success and errors
- ✅ Explicit response model for type safety
- ✅ Real-time update documentation
- ✅ Clear summary and tags

## Step-by-Step Migration

### Step 1: Import Examples

Add at the top of your API routes file:

```python
from app.src.config.openapi_examples import (
    PLAYER_STATUS_EXAMPLE,
    PLAYER_PLAY_EXAMPLE,
    ERROR_404_EXAMPLE,
    ERROR_400_EXAMPLE,
    ERROR_503_EXAMPLE,
    COMMON_ERROR_RESPONSES
)
```

### Step 2: Define Response Models (Optional but Recommended)

```python
from pydantic import BaseModel, Field
from typing import Optional

class TrackInfo(BaseModel):
    """Track information model."""
    id: str
    name: str
    artist: Optional[str] = None
    duration_ms: int

class PlayerStatusData(BaseModel):
    """Player status data model."""
    is_playing: bool = Field(..., description="Whether audio is currently playing")
    current_track: Optional[TrackInfo] = Field(None, description="Current track info")
    position_ms: int = Field(..., ge=0, description="Playback position in milliseconds")
    volume: int = Field(..., ge=0, le=100, description="Volume level")
    playlist_id: Optional[str] = Field(None, description="Current playlist ID")
```

### Step 3: Enhance Route Decorator

```python
@self.router.get(
    "/status",
    summary="Get player status",  # Short, appears in sidebar
    description="""             # Detailed, appears in docs
    Retrieve current playback status.

    **Returns**:
    - Playback state (playing/paused/stopped)
    - Current track with metadata
    - Position and duration
    - Volume level

    **WebSocket**: Broadcasts `state:player` on changes
    """,
    response_model=SuccessResponse[PlayerStatusData],  # Type safety
    responses={                # Examples for documentation
        200: PLAYER_STATUS_EXAMPLE,
        503: ERROR_503_EXAMPLE
    },
    tags=["player"]  # Group with related endpoints
)
```

### Step 4: Add Request Examples (if applicable)

```python
from fastapi import Body

@self.router.post(
    "/volume",
    summary="Set volume level",
    responses={200: PLAYER_VOLUME_EXAMPLE}
)
async def set_volume(
    request: Request,
    body: VolumeRequest = Body(
        ...,
        examples={
            "half_volume": {
                "summary": "Set to 50%",
                "value": {"volume": 50, "client_op_id": "vol_001"}
            },
            "full_volume": {
                "summary": "Set to 100%",
                "value": {"volume": 100, "client_op_id": "vol_002"}
            }
        }
    )
):
    # Implementation
    pass
```

## Complete Example: Playlist Endpoint

### Before

```python
@self.router.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: str):
    """Get playlist."""
    result = await self._service.get_playlist(playlist_id)
    return result
```

### After

```python
from fastapi import Path
from app.src.config.openapi_examples import (
    PLAYLIST_DETAIL_EXAMPLE,
    ERROR_404_EXAMPLE
)

class PlaylistData(BaseModel):
    """Playlist data model."""
    id: str
    name: str
    created_at: str
    tracks: List[TrackInfo]
    track_count: int
    duration_ms: int
    nfc_tag_id: Optional[str] = None

@self.router.get(
    "/playlists/{playlist_id}",
    summary="Get playlist by ID",
    description="""
    Retrieve a specific playlist with all tracks and metadata.

    **Features**:
    - Complete track listing with metadata
    - NFC tag association (if exists)
    - Total duration calculation
    - Track count

    **WebSocket**: Clients in `playlist:{id}` room receive
    `state:playlist` events when this playlist changes.

    **Errors**:
    - `404`: Playlist not found
    """,
    response_model=SuccessResponse[PlaylistData],
    responses={
        200: PLAYLIST_DETAIL_EXAMPLE,
        404: ERROR_404_EXAMPLE
    },
    tags=["playlists"]
)
async def get_playlist(
    playlist_id: str = Path(
        ...,
        description="Unique playlist identifier",
        example="playlist_123"
    )
):
    """Get playlist with comprehensive documentation."""
    result = await self._service.get_playlist(playlist_id)

    if not result.get("success"):
        return UnifiedResponseService.not_found(
            message="Playlist not found",
            details={"playlist_id": playlist_id}
        )

    return UnifiedResponseService.success(
        message="Playlist retrieved successfully",
        data=result.get("data")
    )
```

## Quick Reference: Common Patterns

### Pattern 1: Simple GET with Examples

```python
@self.router.get(
    "/resource",
    responses={200: SUCCESS_EXAMPLE, 404: ERROR_404_EXAMPLE}
)
```

### Pattern 2: POST with Request Body Examples

```python
@self.router.post(
    "/resource",
    responses={201: CREATED_EXAMPLE, 400: ERROR_400_EXAMPLE}
)
async def create(body: CreateRequest = Body(..., examples={...})):
```

### Pattern 3: Using Combined Response Sets

```python
from app.src.config.openapi_examples import PLAYER_RESPONSES

@self.router.get("/status", responses=PLAYER_RESPONSES)
```

### Pattern 4: Deprecation Notice

```python
@self.router.get(
    "/old-endpoint",
    deprecated=True,
    description="Use `/new-endpoint` instead"
)
```

## Testing Your Changes

### 1. Check Swagger UI

```bash
# Start the application
python app/main.py

# Visit Swagger UI
open http://localhost:8000/docs
```

Verify:
- ✅ Summary appears in sidebar
- ✅ Description appears in endpoint details
- ✅ Examples show in "Example Value" section
- ✅ Response models are documented
- ✅ Tags group endpoints correctly

### 2. Check ReDoc

```bash
open http://localhost:8000/redoc
```

Verify:
- ✅ Clean, professional appearance
- ✅ Examples formatted correctly
- ✅ Navigation sidebar works
- ✅ Search functionality

### 3. Test with curl

```bash
# Get OpenAPI schema
curl http://localhost:8000/openapi.json | jq .

# Verify your endpoint exists
curl http://localhost:8000/openapi.json | \
  jq '.paths["/api/player/status"]'
```

## Common Mistakes to Avoid

### ❌ Wrong: Missing Description

```python
@self.router.get("/status")  # No docs
async def get_status():
    pass
```

### ✅ Right: With Description

```python
@self.router.get(
    "/status",
    summary="Get status",
    description="Detailed description..."
)
async def get_status():
    pass
```

### ❌ Wrong: No Response Examples

```python
responses={200: {"example": {...}}}  # Wrong format
```

### ✅ Right: Proper Response Format

```python
responses={
    200: {
        "description": "Success",
        "content": {
            "application/json": {
                "example": {...}
            }
        }
    }
}
```

### ❌ Wrong: Generic Error Messages

```python
return {"error": "Failed"}  # Not helpful
```

### ✅ Right: Detailed Error Response

```python
return UnifiedResponseService.not_found(
    message="Playlist not found",
    details={"playlist_id": playlist_id, "searched_in": "database"}
)
```

## Checklist

When enhancing an endpoint, ensure:

- [ ] Summary (short, appears in sidebar)
- [ ] Description (detailed, with formatting)
- [ ] Response model (for type safety)
- [ ] Success example (200/201/204)
- [ ] Error examples (400/404/409/429/503)
- [ ] Tags (for grouping)
- [ ] Path/Query/Body parameter descriptions
- [ ] Deprecation notice (if applicable)
- [ ] WebSocket event documentation (if applicable)

## Next Steps

1. **Start with high-traffic endpoints**: Player, Playlist CRUD
2. **Add response models**: Improves type safety and docs
3. **Create custom examples**: Tailor to your use cases
4. **Test thoroughly**: Both Swagger UI and ReDoc
5. **Update incrementally**: One module at a time

## Resources

- [OpenAPI Developer Guide](./openapi-developer-guide.md)
- [API Documentation](./api-socketio-communication.md)
- [Response Models Reference](../back/app/src/common/response_models.py)
- [Examples Library](../back/app/src/config/openapi_examples.py)
