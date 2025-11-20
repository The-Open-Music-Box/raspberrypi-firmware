# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified data models for TheOpenMusicBox.

This module defines all data models used across the backend and frontend,
ensuring consistent field names, types, and serialization formats.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_serializer
from datetime import datetime
from enum import Enum


class PlaybackState(str, Enum):
    """Standardized playback state values."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    LOADING = "loading"
    ERROR = "error"


class UploadStatus(str, Enum):
    """Standardized upload status values."""

    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class TrackModel(BaseModel):
    """Unified Track model - consistent across frontend/backend."""

    id: str = Field(..., description="Unique track identifier")
    title: str = Field(..., description="Track title")
    filename: str = Field(..., description="Original filename")
    duration_ms: int = Field(..., description="Track duration in milliseconds")
    file_path: str = Field(..., description="Server file path")
    file_hash: Optional[str] = Field(None, description="File content hash")
    file_size: Optional[int] = Field(None, description="File size in bytes")

    # Metadata fields
    artist: Optional[str] = Field(None, description="Track artist")
    album: Optional[str] = Field(None, description="Track album")
    track_number: Optional[int] = Field(None, description="Track number in album")

    # Statistics
    play_count: int = Field(0, description="Number of times played")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # State synchronization
    server_seq: int = Field(..., description="Server sequence number")

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, v):
        """Ensure duration is non-negative."""
        if v < 0:
            raise ValueError("Duration cannot be negative")
        return v

    @model_serializer
    def serialize_model(self):
        """Custom serializer for datetime fields."""
        data = self.__dict__.copy()
        if "created_at" in data and data["created_at"]:
            data["created_at"] = data["created_at"].isoformat()
        if "updated_at" in data and data["updated_at"]:
            data["updated_at"] = data["updated_at"].isoformat()
        return data

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PlaylistModel(BaseModel):
    """Unified Playlist model - resolves name/title confusion."""

    id: str = Field(..., description="Unique playlist identifier")
    title: str = Field(..., description="Playlist title (resolved from name/title confusion)")
    description: str = Field("", description="Playlist description")

    # NFC integration
    nfc_tag_id: Optional[str] = Field(None, description="Associated NFC tag ID")

    # Tracks
    tracks: List[TrackModel] = Field(default_factory=list, description="Playlist tracks")
    track_count: int = Field(0, description="Number of tracks in playlist")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # State synchronization
    server_seq: int = Field(..., description="Global server sequence")
    playlist_seq: int = Field(..., description="Playlist-specific sequence")

    @field_validator("track_count", mode="after")
    @classmethod
    def validate_track_count(cls, v, info):
        """Ensure track_count matches tracks length."""
        if info.data and "tracks" in info.data:
            tracks = info.data.get("tracks", [])
            return len(tracks)
        return v

    @model_serializer
    def serialize_model(self):
        """Custom serializer for datetime fields."""
        data = self.__dict__.copy()
        if "created_at" in data and data["created_at"]:
            data["created_at"] = data["created_at"].isoformat()
        if "updated_at" in data and data["updated_at"]:
            data["updated_at"] = data["updated_at"].isoformat()
        return data

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PlaylistLiteModel(BaseModel):
    """Lightweight playlist model for list views."""

    id: str = Field(..., description="Unique playlist identifier")
    title: str = Field(..., description="Playlist title")
    description: str = Field("", description="Playlist description")
    nfc_tag_id: Optional[str] = Field(None, description="Associated NFC tag ID")
    track_count: int = Field(0, description="Number of tracks in playlist")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    server_seq: int = Field(..., description="Global server sequence")

    @model_serializer
    def serialize_model(self):
        """Custom serializer for datetime fields."""
        data = self.__dict__.copy()
        if "created_at" in data and data["created_at"]:
            data["created_at"] = data["created_at"].isoformat()
        if "updated_at" in data and data["updated_at"]:
            data["updated_at"] = data["updated_at"].isoformat()
        return data

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PlayerStateModel(BaseModel):
    """Unified PlayerState model - consistent across all endpoints."""

    # Playback state
    is_playing: bool = Field(..., description="Whether audio is currently playing")
    state: PlaybackState = Field(..., description="Detailed playback state")

    # Current playlist/track
    active_playlist_id: Optional[str] = Field(None, description="Currently active playlist ID")
    active_playlist_title: Optional[str] = Field(
        None, description="Currently active playlist title"
    )
    active_track_id: Optional[str] = Field(None, description="Currently active track ID")
    active_track: Optional[TrackModel] = Field(None, description="Currently active track")

    # Playback position
    position_ms: int = Field(0, description="Current playback position in milliseconds")
    duration_ms: int = Field(0, description="Total track duration in milliseconds")

    # Playlist navigation
    track_index: int = Field(0, description="Current track index in playlist")
    track_count: int = Field(0, description="Total tracks in current playlist")
    can_prev: bool = Field(False, description="Whether previous track is available")
    can_next: bool = Field(False, description="Whether next track is available")

    # Audio control
    volume: int = Field(100, ge=0, le=100, description="Current volume level (0-100)")
    muted: bool = Field(False, description="Whether audio is muted")

    # State synchronization
    server_seq: int = Field(..., description="Server sequence number")

    # Optional error information
    error_message: Optional[str] = Field(None, description="Error message if in error state")

    @field_validator("position_ms", "duration_ms")
    @classmethod
    def validate_time_values(cls, v):
        """Ensure time values are non-negative."""
        if v < 0:
            raise ValueError("Time values cannot be negative")
        return v

    @field_validator("track_index")
    @classmethod
    def validate_track_index(cls, v, info):
        """Ensure track_index is within bounds."""
        if info.data and "track_count" in info.data:
            track_count = info.data.get("track_count", 0)
            if track_count > 0 and (v < 0 or v >= track_count):
                raise ValueError("Track index out of bounds")
        return v


class TrackProgressModel(BaseModel):
    """Model for track progress updates."""

    position_ms: int = Field(..., description="Current playback position in milliseconds")
    duration_ms: int = Field(..., description="Total track duration in milliseconds")
    is_playing: bool = Field(..., description="Whether audio is currently playing")
    active_track_id: Optional[str] = Field(None, description="Currently active track ID")
    server_seq: int = Field(..., description="Server sequence number")
    timestamp: int = Field(..., description="Progress timestamp in milliseconds")


class VolumePayloadModel(BaseModel):
    """Model for volume state."""

    volume: int = Field(..., ge=0, le=100, description="Volume level (0-100)")
    muted: bool = Field(False, description="Whether audio is muted")
    server_seq: int = Field(..., description="Server sequence number")


class UploadStatusModel(BaseModel):
    """Unified model for file upload status."""

    session_id: str = Field(..., description="Upload session identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="Total file size in bytes")
    bytes_uploaded: int = Field(0, description="Bytes uploaded so far")
    progress_percent: float = Field(0.0, ge=0.0, le=100.0, description="Upload progress percentage")
    chunks_total: int = Field(..., description="Total number of chunks")
    chunks_uploaded: int = Field(0, description="Number of chunks uploaded")
    status: UploadStatus = Field(..., description="Upload status")
    error_message: Optional[str] = Field(None, description="Error message if upload failed")
    created_at: datetime = Field(..., description="Upload session creation time")
    updated_at: datetime = Field(..., description="Last update time")

    @model_serializer
    def serialize_model(self):
        """Custom serializer for datetime fields."""
        data = self.__dict__.copy()
        if "created_at" in data and data["created_at"]:
            data["created_at"] = data["created_at"].isoformat()
        if "updated_at" in data and data["updated_at"]:
            data["updated_at"] = data["updated_at"].isoformat()
        return data

    model_config = ConfigDict(arbitrary_types_allowed=True)


class NFCAssociationModel(BaseModel):
    """Model for NFC tag associations."""

    tag_id: str = Field(..., description="NFC tag identifier")
    playlist_id: str = Field(..., description="Associated playlist ID")
    playlist_title: str = Field(..., description="Associated playlist title")
    created_at: datetime = Field(..., description="Association creation time")

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        """Parse string to datetime if needed."""
        if isinstance(v, str):
            # Handle different string formats
            if v.endswith("Z"):
                v = v[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                # Fallback to current time if parsing fails
                return datetime.now()
        return v

    @model_serializer
    def serialize_model(self):
        """Custom serializer for datetime fields."""
        data = self.__dict__.copy()
        if "created_at" in data and data["created_at"]:
            data["created_at"] = data["created_at"].isoformat()
        return data

    model_config = ConfigDict(arbitrary_types_allowed=True)


class YouTubeProgressModel(BaseModel):
    """Model for YouTube download progress."""

    task_id: str = Field(..., description="Download task identifier")
    status: str = Field(..., description="Download status")
    progress_percent: float = Field(
        0.0, ge=0.0, le=100.0, description="Download progress percentage"
    )
    current_step: str = Field("", description="Current processing step")
    estimated_time_remaining: Optional[int] = Field(
        None, description="Estimated time remaining in seconds"
    )
    error_message: Optional[str] = Field(None, description="Error message if download failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Download result data")


class YouTubeResultModel(BaseModel):
    """Model for YouTube search results."""

    id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    duration_ms: int = Field(..., description="Video duration in milliseconds")
    thumbnail_url: str = Field(..., description="Video thumbnail URL")
    channel: str = Field(..., description="Channel name")
    view_count: int = Field(0, description="Number of views")
