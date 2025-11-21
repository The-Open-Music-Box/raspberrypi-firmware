# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Socket.IO Configuration Constants

Centralized configuration for all Socket.IO timing, throttling, and performance settings.
Optimized for smooth local playback with minimal delay.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SocketConfig:
    """Configuration constants for Socket.IO event system."""

    # Position update timing - optimized for smooth local playback
    POSITION_UPDATE_INTERVAL_MS: int = 500  # 500ms updates for smooth seekbar progression
    POSITION_THROTTLE_MIN_MS: int = 400  # Minimum time between position updates

    # Player state timing
    PLAYER_STATE_DEBOUNCE_MS: int = 100  # Debounce rapid state changes

    # Outbox and retry configuration
    OUTBOX_RETRY_MAX: int = 3  # Maximum retry attempts
    OUTBOX_SIZE_LIMIT: int = 1000  # Maximum outbox size
    OUTBOX_CLEANUP_BATCH: int = 100  # Events to remove when limit reached

    # Operation deduplication
    OPERATION_DEDUP_WINDOW_SEC: int = 300  # 5 minutes deduplication window
    OPERATION_RESULT_TTL_SEC: int = 600  # 10 minutes result cache TTL

    # Client connection management
    CLIENT_PING_INTERVAL_SEC: int = 30  # Ping clients every 30 seconds
    CLIENT_TIMEOUT_SEC: int = 60  # Consider client dead after 60 seconds

    # Event payload optimization
    COMPRESS_PAYLOADS_OVER_BYTES: int = 1024  # Compress large payloads
    MAX_EVENT_BATCH_SIZE: int = 50  # Maximum events per batch

    # Logging configuration
    LOG_POSITION_EVENTS: bool = False  # Don't log frequent position events
    LOG_CONNECTION_EVENTS: bool = True  # Log connect/disconnect
    LOG_ERROR_EVENTS: bool = True  # Always log errors

    @classmethod
    def get_position_update_config(cls) -> Dict[str, Any]:
        """Get configuration specifically for position updates."""
        return {
            "interval_ms": cls.POSITION_UPDATE_INTERVAL_MS,
            "throttle_min_ms": cls.POSITION_THROTTLE_MIN_MS,
            "log_events": cls.LOG_POSITION_EVENTS,
        }

    @classmethod
    def get_outbox_config(cls) -> Dict[str, Any]:
        """Get configuration for outbox processing."""
        return {
            "retry_max": cls.OUTBOX_RETRY_MAX,
            "size_limit": cls.OUTBOX_SIZE_LIMIT,
            "cleanup_batch": cls.OUTBOX_CLEANUP_BATCH,
        }

    @classmethod
    def get_dedup_config(cls) -> Dict[str, Any]:
        """Get configuration for operation deduplication."""
        return {
            "window_sec": cls.OPERATION_DEDUP_WINDOW_SEC,
            "result_ttl_sec": cls.OPERATION_RESULT_TTL_SEC,
        }

    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration values for consistency and safety."""
        issues = []

        # Validate timing values
        if cls.POSITION_UPDATE_INTERVAL_MS < 50:
            issues.append("POSITION_UPDATE_INTERVAL_MS too low (minimum 50ms)")
        if cls.POSITION_UPDATE_INTERVAL_MS > 5000:
            issues.append("POSITION_UPDATE_INTERVAL_MS too high (maximum 5000ms)")

        if cls.POSITION_THROTTLE_MIN_MS >= cls.POSITION_UPDATE_INTERVAL_MS:
            issues.append("POSITION_THROTTLE_MIN_MS must be less than POSITION_UPDATE_INTERVAL_MS")

        # Validate size limits
        if cls.OUTBOX_SIZE_LIMIT < 100:
            issues.append("OUTBOX_SIZE_LIMIT too low (minimum 100)")
        if cls.OUTBOX_CLEANUP_BATCH >= cls.OUTBOX_SIZE_LIMIT:
            issues.append("OUTBOX_CLEANUP_BATCH must be less than OUTBOX_SIZE_LIMIT")

        # Validate time windows
        if cls.OPERATION_RESULT_TTL_SEC < cls.OPERATION_DEDUP_WINDOW_SEC:
            issues.append("OPERATION_RESULT_TTL_SEC should be >= OPERATION_DEDUP_WINDOW_SEC")

        if issues:
            import logging
            logger = logging.getLogger(__name__)
            for issue in issues:
                logger.error(f"Socket config validation error: {issue}")
            return False

        return True


# Global instance for easy access
# Note: SocketConfig should be retrieved from DI container
# Use: container.get("socket_config") or get_socket_config()
# Legacy global instance kept for backward compatibility during transition
socket_config = SocketConfig()

# Validate configuration on import
if not SocketConfig.validate_config():
    raise ValueError("Socket configuration validation failed - check logs for details")
