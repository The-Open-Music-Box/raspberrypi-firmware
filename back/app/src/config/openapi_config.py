# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
OpenAPI/Swagger Configuration for TheOpenMusicBox

This module provides comprehensive OpenAPI documentation configuration including:
- API metadata (title, description, version, contact, license)
- Organized tags with descriptions
- Custom schema customization
- Response examples
- Security schemes (for future authentication)
"""

from typing import Dict, List, Any

# API Metadata
API_TITLE = "TheOpenMusicBox API"
API_VERSION = "3.0.0"  # DDD Architecture version
API_DESCRIPTION = """
# TheOpenMusicBox API

**Server-Authoritative Music Management System with Domain-Driven Design**

TheOpenMusicBox provides a comprehensive music management and playback system designed for Raspberry Pi with NFC tag support. The API follows Domain-Driven Design (DDD) principles with clean architecture separation.

## Key Features

- 🎵 **Audio Playback Control**: Play, pause, stop, seek, and volume control
- 📋 **Playlist Management**: CRUD operations for playlists and tracks
- 🏷️ **NFC Integration**: Associate NFC tags with playlists for physical playback
- 📤 **File Upload**: Chunked upload support for audio files
- 🎬 **YouTube Integration**: Download audio from YouTube videos
- 🔄 **Real-time Updates**: Socket.IO for live state synchronization
- 🎛️ **Physical Controls**: GPIO button support for hardware control

## Architecture

### Domain-Driven Design (DDD)

The API is built with clean architecture principles:

1. **Domain Layer**: Pure business logic (playlists, tracks, playback rules)
2. **Application Layer**: Use cases and orchestration
3. **Infrastructure Layer**: Database, hardware adapters (NFC, GPIO, audio)
4. **API Layer**: HTTP endpoints and WebSocket handlers

### Two-Layer Routing

- **Layer 1 (Pure API Routes)**: HTTP request/response handling
- **Layer 2 (Bootstrap Routes)**: Dependency injection and lifecycle management

### State Management

Server-authoritative architecture with:
- **UnifiedStateManager**: Centralized state coordination
- **EventOutbox**: Reliable event delivery with retry
- **StateEventCoordinator**: DDD event coordination
- **ClientSubscriptionManager**: Room-based subscriptions

## Response Format

All endpoints return standardized responses:

```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": { ... },
  "server_seq": 12345,
  "timestamp": 1704067200000
}
```

## Real-Time Communication

Socket.IO events for real-time updates:
- `state:player` - Player state changes
- `state:playlists` - Playlist collection updates
- `state:playlist` - Specific playlist updates
- `state:track_position` - Position updates (500ms interval)
- `upload:progress` - File upload progress
- `nfc_association_state` - NFC tag association status

## Authentication

Currently designed for local network use without authentication. Future versions will support:
- API key authentication
- OAuth 2.0 integration
- Role-based access control (RBAC)

## Rate Limiting

Rate limiting is implemented via the OperationsService:
- Player controls: Prevent rapid-fire commands
- File uploads: Limit concurrent sessions
- YouTube downloads: Prevent API abuse

## Error Handling

Standardized error responses with:
- `error_type`: Structured error classification
- `message`: Human-readable description
- `details`: Additional context
- `request_id`: For debugging

## Getting Started

1. **Base URL**: Typically `http://localhost:8000` or `http://<raspberry-pi-ip>:8000`
2. **WebSocket**: `ws://localhost:8000/socket.io/`
3. **Documentation**:
   - Swagger UI: `/docs`
   - ReDoc: `/redoc`
   - OpenAPI Schema: `/openapi.json`

## Support

- **GitHub**: [TheOpenMusicBox Repository](https://github.com/yourusername/theopenmusicbox)
- **License**: Non-commercial use only
- **Documentation**: See `/documentation` folder in repository
"""

# Contact Information
API_CONTACT = {
    "name": "Jonathan Piette",
    "email": "contact@theopenmusicbox.com",
}

# License Information
API_LICENSE = {
    "name": "Non-Commercial License",
    "url": "https://github.com/yourusername/theopenmusicbox/blob/main/LICENSE",
}

# Organized Tags with Descriptions
API_TAGS_METADATA = [
    {
        "name": "player",
        "description": """
**Player Control Operations**

Control audio playback with play, pause, stop, seek, and volume operations.
All player operations broadcast real-time state changes via Socket.IO.

**Key Endpoints**:
- Play/Pause/Stop playback
- Seek to position
- Volume control
- Get player status

**WebSocket Events**: `state:player`, `state:track_position`
        """,
    },
    {
        "name": "playlists",
        "description": """
**Playlist Management**

Complete CRUD operations for playlists and tracks with real-time synchronization.

**Features**:
- Create, read, update, delete playlists
- Track management (add, delete, reorder)
- Start playlist playback
- Move tracks between playlists
- Sync playlists with filesystem

**WebSocket Events**: `state:playlists`, `state:playlist`, `state:track`

**Architecture**: Split into 6 specialized modules for better maintainability.
        """,
    },
    {
        "name": "nfc",
        "description": """
**NFC Tag Integration**

Associate NFC tags with playlists for physical playback control.

**Features**:
- Tag association with playlists
- Tag scanning and detection
- Override existing associations
- Real-time association status

**Hardware Support**: PN532 NFC reader via I2C/UART

**WebSocket Events**: `nfc_status`, `nfc_association_state`

**States**: waiting, duplicate, success, timeout, cancelled, error
        """,
    },
    {
        "name": "uploads",
        "description": """
**File Upload Management**

Chunked file upload system with progress tracking and real-time updates.

**Features**:
- Initialize upload sessions
- Chunked upload (configurable chunk size)
- Progress tracking
- Automatic finalization
- Session management

**Supported Formats**: MP3, FLAC, WAV, OGG, M4A

**WebSocket Events**: `upload:progress`, `upload:complete`, `upload:error`
        """,
    },
    {
        "name": "youtube",
        "description": """
**YouTube Integration**

Download audio from YouTube videos and add to playlists.

**Features**:
- Download from YouTube URL
- Progress tracking
- Video search
- Automatic format conversion
- Metadata extraction

**WebSocket Events**: `youtube:progress`, `youtube:complete`, `youtube:error`

**External Dependency**: yt-dlp for video processing
        """,
    },
    {
        "name": "system",
        "description": """
**System Management**

Health checks, system information, and status monitoring.

**Features**:
- Health check endpoint
- System information
- Playback status (anti-cache)
- System logs
- Restart capability

**Monitoring**: Provides metrics for observability and debugging
        """,
    },
    {
        "name": "websocket",
        "description": """
**WebSocket (Socket.IO) Events**

Real-time bidirectional communication for state synchronization.

**Event Categories**:
- Connection management (connect, disconnect)
- Subscription management (join/leave rooms)
- State synchronization (state:* events)
- Operation acknowledgments (ack:op, err:op)

**Architecture**: Server-authoritative state management with EventOutbox retry logic

**Rooms**:
- `playlists` - Global playlist updates
- `playlist:{id}` - Specific playlist updates
- `nfc:{assoc_id}` - NFC association session
        """,
    },
]

# Custom OpenAPI Schema Modifications
def customize_openapi_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Customize the OpenAPI schema with additional information and examples.

    Args:
        schema: The base OpenAPI schema generated by FastAPI

    Returns:
        Modified OpenAPI schema with enhancements
    """
    # Add servers configuration
    schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development server (local)"
        },
        {
            "url": "http://{host}:8000",
            "description": "Raspberry Pi server",
            "variables": {
                "host": {
                    "default": "raspberrypi.local",
                    "description": "Raspberry Pi hostname or IP address"
                }
            }
        }
    ]

    # Add external documentation
    schema["externalDocs"] = {
        "description": "Complete API Documentation",
        "url": "https://github.com/yourusername/theopenmusicbox/blob/main/documentation/api-socketio-communication.md"
    }

    # Add security schemes (for future authentication)
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication (future feature)"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT bearer token authentication (future feature)"
        }
    }

    # Add common response examples to schemas
    if "components" in schema and "schemas" in schema["components"]:
        # Add example to BaseResponse
        if "BaseResponse" in schema["components"]["schemas"]:
            schema["components"]["schemas"]["BaseResponse"]["example"] = {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {"example_field": "example_value"},
                "timestamp": 1704067200000,
                "server_seq": 12345
            }

        # Add example to ErrorResponse
        if "ErrorResponse" in schema["components"]["schemas"]:
            schema["components"]["schemas"]["ErrorResponse"]["example"] = {
                "status": "error",
                "message": "Resource not found",
                "error_type": "not_found",
                "details": {"resource_id": "playlist_123"},
                "timestamp": 1704067200000,
                "request_id": "abc12345"
            }

    # Add custom x-logo extension for branding
    schema["info"]["x-logo"] = {
        "url": "https://raw.githubusercontent.com/yourusername/theopenmusicbox/main/docs/logo.png",
        "altText": "TheOpenMusicBox Logo"
    }

    # Add API lifecycle information
    schema["info"]["x-api-lifecycle"] = {
        "status": "stable",
        "version": "3.0.0",
        "architecture": "DDD (Domain-Driven Design)",
        "last_updated": "2025-01-01"
    }

    return schema


# Response Examples for Common Scenarios
RESPONSE_EXAMPLES = {
    "player_status_success": {
        "summary": "Player status retrieved successfully",
        "value": {
            "status": "success",
            "message": "Player status retrieved",
            "data": {
                "is_playing": True,
                "current_track": {
                    "id": "track_123",
                    "name": "Example Song.mp3",
                    "duration_ms": 240000
                },
                "position_ms": 60000,
                "volume": 75,
                "playlist_id": "playlist_456"
            },
            "timestamp": 1704067200000,
            "server_seq": 12345
        }
    },
    "playlist_created_success": {
        "summary": "Playlist created successfully",
        "value": {
            "status": "success",
            "message": "Playlist created successfully",
            "data": {
                "id": "playlist_789",
                "name": "My Playlist",
                "created_at": "2025-01-01T12:00:00Z",
                "tracks": []
            },
            "timestamp": 1704067200000,
            "server_seq": 12346
        }
    },
    "not_found_error": {
        "summary": "Resource not found",
        "value": {
            "status": "error",
            "message": "Playlist not found",
            "error_type": "not_found",
            "details": {"playlist_id": "playlist_123"},
            "timestamp": 1704067200000,
            "request_id": "abc12345"
        }
    },
    "validation_error": {
        "summary": "Validation error",
        "value": {
            "status": "error",
            "message": "Invalid request parameters",
            "error_type": "validation_error",
            "details": {
                "volume": "Volume must be between 0 and 100"
            },
            "timestamp": 1704067200000,
            "request_id": "def67890"
        }
    }
}


# OpenAPI configuration for FastAPI
def get_openapi_config() -> Dict[str, Any]:
    """
    Get the complete OpenAPI configuration for FastAPI initialization.

    Returns:
        Dictionary with OpenAPI configuration parameters
    """
    return {
        "title": API_TITLE,
        "version": API_VERSION,
        "description": API_DESCRIPTION,
        "contact": API_CONTACT,
        "license_info": API_LICENSE,
        "openapi_tags": API_TAGS_METADATA,
    }
