# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Pagination utilities for the paginated playlists index optimization.
Provides cursor-based pagination with opaque cursor encoding/decoding.
"""

import base64
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


def encode_cursor(updated_at: str, playlist_id: str) -> str:
    """
    Encode pagination cursor from sort key components.

    Args:
        updated_at: ISO timestamp string for updated_at field
        playlist_id: Playlist ID for tie-breaking

    Returns:
        Base64-encoded opaque cursor string
    """
    cursor_data = {"updated_at": updated_at, "id": playlist_id}
    cursor_json = json.dumps(cursor_data, separators=(",", ":"))
    return base64.b64encode(cursor_json.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Decode pagination cursor to sort key components.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Tuple of (updated_at, playlist_id) or (None, None) if invalid
    """
    try:
        cursor_json = base64.b64decode(cursor.encode("ascii")).decode("utf-8")
        cursor_data = json.loads(cursor_json)
        return cursor_data.get("updated_at"), cursor_data.get("id")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None, None


def compute_playlist_aggregates(tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate values for a playlist from its tracks.

    Args:
        tracks: List of track dictionaries

    Returns:
        Dictionary with computed aggregates: track_count, total_duration_ms
    """
    track_count = len(tracks)
    total_duration_ms = 0

    for track in tracks:
        # Check for duration_ms first (preferred), then duration (fallback)
        duration_ms = track.get("duration_ms")
        duration = track.get("duration")

        if duration_ms and isinstance(duration_ms, (int, float)) and duration_ms > 0:
            # Already in milliseconds
            total_duration_ms += int(duration_ms)
        elif duration and isinstance(duration, (int, float)) and duration > 0:
            # Check if it's likely already in milliseconds (>1000 suggests ms, not seconds)
            # Most songs are between 30s (30000ms) and 20min (1200000ms)
            if duration > 1000:
                # Already in milliseconds
                total_duration_ms += int(duration)
            else:
                # In seconds, convert to milliseconds
                total_duration_ms += int(duration * 1000)

    return {"track_count": track_count, "total_duration_ms": total_duration_ms}


def create_playlist_index_item(
    playlist_data: Dict[str, Any], server_seq: int, playlist_seq: int
) -> Dict[str, Any]:
    """
    Create a playlist index item from full playlist data.

    Args:
        playlist_data: Full playlist dictionary
        server_seq: Current server sequence number
        playlist_seq: Current playlist sequence number

    Returns:
        Playlist index item dictionary
    """
    tracks = playlist_data.get("tracks", [])
    aggregates = compute_playlist_aggregates(tracks)

    # Ensure updated_at is present, use created_at or current time as fallback
    updated_at = playlist_data.get("updated_at") or playlist_data.get("created_at")
    if not updated_at:
        updated_at = datetime.utcnow().isoformat() + "Z"
    elif not updated_at.endswith("Z") and "+" not in updated_at:
        # Ensure ISO format with Z suffix
        if "." in updated_at:
            updated_at = updated_at.split(".")[0] + "Z"
        elif "T" in updated_at:
            updated_at = updated_at + "Z"
        else:
            updated_at = datetime.utcnow().isoformat() + "Z"

    return {
        "id": playlist_data["id"],
        "title": playlist_data.get("title", "Untitled"),
        "summary": {
            "track_count": aggregates["track_count"],
            "total_duration_ms": aggregates["total_duration_ms"],
            "updated_at": updated_at,
        },
        "nfc_tag_id": playlist_data.get("nfc_tag_id"),
        "cover_thumb_url": None,  # Thumbnail generation not yet implemented
        "server_seq": server_seq,
        "playlist_seq": playlist_seq,
    }
