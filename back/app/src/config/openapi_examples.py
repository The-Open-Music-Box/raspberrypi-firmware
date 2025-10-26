# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
OpenAPI Response Examples

This module provides reusable response examples for OpenAPI documentation.
Use these examples in FastAPI route decorators to enhance API documentation.

Usage:
    from app.src.config.openapi_examples import PLAYER_STATUS_EXAMPLE, ERROR_404_EXAMPLE

    @router.get("/status", responses={200: PLAYER_STATUS_EXAMPLE, 404: ERROR_404_EXAMPLE})
    async def get_status():
        ...
"""

from typing import Dict, Any

# ============================================================================
# PLAYER EXAMPLES
# ============================================================================

PLAYER_STATUS_EXAMPLE = {
    "description": "Successful player status retrieval",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Player status retrieved successfully",
                "data": {
                    "is_playing": True,
                    "current_track": {
                        "id": "track_123",
                        "name": "Example Song.mp3",
                        "artist": "Example Artist",
                        "duration_ms": 240000,
                        "file_path": "/music/playlists/playlist_456/Example Song.mp3"
                    },
                    "position_ms": 60000,
                    "volume": 75,
                    "playlist_id": "playlist_456",
                    "is_repeat": False,
                    "is_shuffle": False
                },
                "timestamp": 1704067200000,
                "server_seq": 12345
            }
        }
    }
}

PLAYER_PLAY_EXAMPLE = {
    "description": "Playback started successfully",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Playback started successfully",
                "data": {
                    "is_playing": True,
                    "current_track": {
                        "id": "track_789",
                        "name": "New Song.mp3"
                    },
                    "volume": 75
                },
                "timestamp": 1704067200000,
                "server_seq": 12346
            }
        }
    }
}

PLAYER_VOLUME_EXAMPLE = {
    "description": "Volume changed successfully",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Volume set to 80%",
                "data": {
                    "volume": 80,
                    "is_playing": True
                },
                "timestamp": 1704067200000,
                "server_seq": 12347
            }
        }
    }
}

# ============================================================================
# PLAYLIST EXAMPLES
# ============================================================================

PLAYLIST_LIST_EXAMPLE = {
    "description": "Playlists retrieved successfully",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Playlists retrieved successfully",
                "data": {
                    "items": [
                        {
                            "id": "playlist_123",
                            "name": "My Favorites",
                            "track_count": 15,
                            "duration_ms": 3600000,
                            "created_at": "2025-01-01T12:00:00Z",
                            "nfc_tag_id": "04:A3:B2:C1"
                        },
                        {
                            "id": "playlist_456",
                            "name": "Workout Mix",
                            "track_count": 22,
                            "duration_ms": 5400000,
                            "created_at": "2025-01-02T14:30:00Z",
                            "nfc_tag_id": None
                        }
                    ],
                    "page": 1,
                    "limit": 20,
                    "total": 2,
                    "total_pages": 1
                },
                "timestamp": 1704067200000,
                "server_seq": 12348
            }
        }
    }
}

PLAYLIST_DETAIL_EXAMPLE = {
    "description": "Playlist retrieved successfully",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Playlist retrieved successfully",
                "data": {
                    "id": "playlist_123",
                    "name": "My Favorites",
                    "created_at": "2025-01-01T12:00:00Z",
                    "nfc_tag_id": "04:A3:B2:C1",
                    "tracks": [
                        {
                            "id": "track_1",
                            "name": "Song 1.mp3",
                            "artist": "Artist 1",
                            "duration_ms": 240000,
                            "track_number": 1,
                            "file_path": "/music/playlists/playlist_123/Song 1.mp3"
                        },
                        {
                            "id": "track_2",
                            "name": "Song 2.mp3",
                            "artist": "Artist 2",
                            "duration_ms": 210000,
                            "track_number": 2,
                            "file_path": "/music/playlists/playlist_123/Song 2.mp3"
                        }
                    ],
                    "track_count": 2,
                    "duration_ms": 450000
                },
                "timestamp": 1704067200000,
                "server_seq": 12349
            }
        }
    }
}

PLAYLIST_CREATED_EXAMPLE = {
    "description": "Playlist created successfully",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Playlist created successfully",
                "data": {
                    "id": "playlist_789",
                    "name": "New Playlist",
                    "created_at": "2025-01-03T10:00:00Z",
                    "tracks": [],
                    "track_count": 0,
                    "duration_ms": 0
                },
                "timestamp": 1704067200000,
                "server_seq": 12350
            }
        }
    }
}

# ============================================================================
# NFC EXAMPLES
# ============================================================================

NFC_ASSOCIATION_SUCCESS_EXAMPLE = {
    "description": "NFC tag associated successfully",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "NFC tag associated successfully",
                "data": {
                    "playlist_id": "playlist_123",
                    "tag_id": "04:A3:B2:C1",
                    "associated_at": "2025-01-03T11:00:00Z"
                },
                "timestamp": 1704067200000,
                "server_seq": 12351
            }
        }
    }
}

NFC_STATUS_EXAMPLE = {
    "description": "NFC reader status retrieved",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "NFC reader status retrieved",
                "data": {
                    "reader_available": True,
                    "scanning": False,
                    "association_active": False,
                    "current_session_id": None,
                    "hardware_type": "PN532",
                    "connection": "I2C"
                },
                "timestamp": 1704067200000,
                "server_seq": 12352
            }
        }
    }
}

# ============================================================================
# UPLOAD EXAMPLES
# ============================================================================

UPLOAD_SESSION_CREATED_EXAMPLE = {
    "description": "Upload session initialized",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Upload session initialized",
                "data": {
                    "session_id": "upload_abc123",
                    "playlist_id": "playlist_456",
                    "filename": "new_song.mp3",
                    "total_chunks": 10,
                    "chunk_size": 1048576,
                    "expires_at": "2025-01-03T12:00:00Z"
                },
                "timestamp": 1704067200000,
                "server_seq": 12353
            }
        }
    }
}

UPLOAD_PROGRESS_EXAMPLE = {
    "description": "Upload chunk processed",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "Chunk uploaded successfully",
                "data": {
                    "session_id": "upload_abc123",
                    "chunk_index": 5,
                    "total_chunks": 10,
                    "progress_percent": 50.0,
                    "bytes_uploaded": 5242880,
                    "total_bytes": 10485760
                },
                "timestamp": 1704067200000,
                "server_seq": 12354
            }
        }
    }
}

# ============================================================================
# YOUTUBE EXAMPLES
# ============================================================================

YOUTUBE_DOWNLOAD_STARTED_EXAMPLE = {
    "description": "YouTube download started",
    "content": {
        "application/json": {
            "example": {
                "status": "success",
                "message": "YouTube download started",
                "data": {
                    "task_id": "yt_task_123",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "playlist_id": "playlist_789",
                    "status": "downloading",
                    "estimated_time_seconds": 30
                },
                "timestamp": 1704067200000,
                "server_seq": 12355
            }
        }
    }
}

# ============================================================================
# ERROR EXAMPLES
# ============================================================================

ERROR_400_EXAMPLE = {
    "description": "Bad request - invalid parameters",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "message": "Invalid request parameters",
                "error_type": "validation_error",
                "details": {
                    "field": "volume",
                    "error": "Volume must be between 0 and 100",
                    "provided_value": 150
                },
                "timestamp": 1704067200000,
                "request_id": "req_abc123"
            }
        }
    }
}

ERROR_404_EXAMPLE = {
    "description": "Resource not found",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "message": "Playlist not found",
                "error_type": "not_found",
                "details": {
                    "resource_type": "playlist",
                    "resource_id": "playlist_999"
                },
                "timestamp": 1704067200000,
                "request_id": "req_def456"
            }
        }
    }
}

ERROR_409_EXAMPLE = {
    "description": "Conflict - resource already exists or state conflict",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "message": "NFC tag already associated with another playlist",
                "error_type": "conflict",
                "details": {
                    "tag_id": "04:A3:B2:C1",
                    "existing_playlist_id": "playlist_123",
                    "existing_playlist_name": "My Favorites"
                },
                "timestamp": 1704067200000,
                "request_id": "req_ghi789"
            }
        }
    }
}

ERROR_429_EXAMPLE = {
    "description": "Rate limit exceeded",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "message": "Too many requests, please slow down",
                "error_type": "rate_limit_exceeded",
                "details": {
                    "limit": 10,
                    "window_seconds": 60,
                    "retry_after_seconds": 45
                },
                "timestamp": 1704067200000,
                "request_id": "req_jkl012"
            }
        }
    }
}

ERROR_503_EXAMPLE = {
    "description": "Service unavailable",
    "content": {
        "application/json": {
            "example": {
                "status": "error",
                "message": "NFC service is not available",
                "error_type": "service_unavailable",
                "details": {
                    "service": "nfc",
                    "reason": "Hardware not detected or initialization failed"
                },
                "timestamp": 1704067200000,
                "request_id": "req_mno345"
            }
        }
    }
}

# ============================================================================
# COMBINED RESPONSE SETS
# ============================================================================

COMMON_ERROR_RESPONSES = {
    400: ERROR_400_EXAMPLE,
    404: ERROR_404_EXAMPLE,
    429: ERROR_429_EXAMPLE,
    503: ERROR_503_EXAMPLE
}

PLAYER_RESPONSES = {
    200: PLAYER_STATUS_EXAMPLE,
    **COMMON_ERROR_RESPONSES
}

PLAYLIST_RESPONSES = {
    200: PLAYLIST_DETAIL_EXAMPLE,
    404: ERROR_404_EXAMPLE,
    503: ERROR_503_EXAMPLE
}

NFC_RESPONSES = {
    200: NFC_ASSOCIATION_SUCCESS_EXAMPLE,
    409: ERROR_409_EXAMPLE,
    503: ERROR_503_EXAMPLE
}
