# Logging Guidelines for TheOpenMusicBox

**Version:** 1.0
**Last Updated:** 2025-11-09
**Status:** Active

## Table of Contents

1. [Overview](#overview)
2. [Logging Levels](#logging-levels)
3. [Logging Patterns](#logging-patterns)
4. [Error Context](#error-context)
5. [Best Practices](#best-practices)
6. [Examples](#examples)

---

## Overview

This document defines standardized logging practices for TheOpenMusicBox to ensure:
- **Consistent log output** across all modules
- **Meaningful error context** for debugging
- **Appropriate log levels** for different scenarios
- **Production-ready logging** with proper log management

### Core Principles

1. **Log with Purpose**: Every log statement should provide actionable information
2. **Include Context**: Always provide enough information to reproduce and debug issues
3. **Use Appropriate Levels**: Choose the right log level for each situation
4. **Avoid Over-logging**: Don't flood logs with noise (especially in production)
5. **Security First**: Never log sensitive data (passwords, tokens, personal information)

---

## Logging Levels

### DEBUG (Detailed Information)

**When to Use:**
- Internal state changes during development
- Function entry/exit points
- Variable values during troubleshooting
- Loop iterations in complex algorithms
- Temporary debugging statements

**Characteristics:**
- Most verbose level
- Disabled in production by default
- Performance-intensive logging acceptable here

**Example:**
```python
logger.debug(f"Processing playlist {playlist_id} with {len(tracks)} tracks")
logger.debug(f"Broadcasting position update #{self._position_log_counter}: {position_ms}ms")
```

---

### INFO (General Information)

**When to Use:**
- Successful operation completion
- System state transitions
- Client connections/disconnections
- API endpoint invocations (high-level)
- Configuration changes
- Startup/shutdown events

**Characteristics:**
- Confirms expected behavior
- Helps track system flow
- Minimal performance impact

**Example:**
```python
logger.info(f"Client {sid} subscribed to playlists room")
logger.info(f"Playlist '{playlist_name}' created successfully (ID: {playlist_id})")
logger.info("StateEventCoordinator initialized with clean DDD architecture")
```

---

### WARNING (Degraded Functionality)

**When to Use:**
- Recoverable errors (operation continues)
- Deprecated feature usage
- Resource constraints (disk space, memory)
- Retry attempts
- Fallback to default behavior
- Invalid input that's handled gracefully

**Characteristics:**
- Indicates something unexpected but handled
- System continues operating
- May require attention but not urgent

**Example:**
```python
logger.warning(f"Rate limit approaching for client {client_id}: {request_count}/{limit}")
logger.warning(f"Playlist {playlist_id} not found, returning empty state")
logger.warning("Mock hardware mode enabled - hardware features unavailable")
```

---

### ERROR (Operation Failures)

**When to Use:**
- Operation failures that impact functionality
- Exceptions caught and handled
- External service failures
- Database errors
- File I/O errors
- API endpoint failures

**Characteristics:**
- Indicates something went wrong
- Operation failed but system continues
- **MUST include context** (see [Error Context](#error-context))
- **MUST include exc_info=True** for exceptions

**Example:**
```python
logger.error(
    f"Error in play_player: {str(e)}",
    extra={
        "client_op_id": body.client_op_id,
        "request_id": request.headers.get("X-Request-ID"),
        "operation": "play_player",
    },
    exc_info=True
)
```

---

### CRITICAL (System Failures)

**When to Use:**
- System-wide failures
- Service initialization failures
- Database connection loss
- Critical resource exhaustion
- Security violations
- Unrecoverable errors requiring restart

**Characteristics:**
- Indicates severe problems
- System may need immediate attention or restart
- Triggers alerts in production

**Example:**
```python
logger.critical(
    "Failed to initialize audio engine - playback unavailable",
    extra={"error": str(e), "system_state": "degraded"},
    exc_info=True
)
```

---

## Logging Patterns

### Pattern 1: API Endpoint Logging

**Template:**
```python
@router.post("/endpoint")
@handle_http_errors()
async def endpoint_handler(request: Request, body: RequestModel):
    """Endpoint description."""
    try:
        # Business logic
        result = await service.perform_operation()

        if result.get("success"):
            return UnifiedResponseService.success(
                message="Operation completed successfully",
                data=result.get("data"),
                server_seq=result.get("server_seq"),
                client_op_id=body.client_op_id
            )

    except Exception as e:
        logger.error(
            f"Error in endpoint_handler: {str(e)}",
            extra={
                "client_op_id": body.client_op_id,
                "request_id": request.headers.get("X-Request-ID"),
                "operation": "endpoint_handler",
                # Add operation-specific context
                "resource_id": resource_id,
            },
            exc_info=True
        )
        return UnifiedResponseService.internal_error(
            message="Operation failed",
            operation="endpoint_handler"
        )
```

---

### Pattern 2: Service Operation Logging

**Template:**
```python
class ServiceClass:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @handle_service_errors("service_name")
    async def perform_operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """Perform a specific operation."""
        self.logger.info(f"Starting operation with param1={param1}, param2={param2}")

        try:
            # Perform operation
            result = await self._do_work(param1, param2)

            self.logger.info(f"Operation completed successfully")
            return {"success": True, "result": result}

        except ValueError as e:
            self.logger.warning(f"Invalid input: {str(e)}")
            return {"success": False, "error": "invalid_input"}

        except Exception as e:
            self.logger.error(
                f"Operation failed: {str(e)}",
                extra={
                    "param1": param1,
                    "param2": param2,
                    "operation": "perform_operation"
                },
                exc_info=True
            )
            raise
```

---

### Pattern 3: WebSocket Event Logging

**Template:**
```python
@sio.on("event_name")
@handle_http_errors()
async def handle_event(sid: str, data: Dict[str, Any]) -> None:
    """Handle WebSocket event."""
    logger.info(f"Client {sid} triggered event_name")

    try:
        # Process event
        result = await process_event(data)

        # Emit response
        await sio.emit("response_event", result, room=sid)

    except Exception as e:
        logger.error(
            f"Error handling event_name: {str(e)}",
            extra={
                "client_sid": sid,
                "event": "event_name",
                "data_keys": list(data.keys()),
            },
            exc_info=True
        )
```

---

### Pattern 4: State Change Logging

**Template:**
```python
async def update_state(self, new_state: str) -> None:
    """Update system state."""
    old_state = self._current_state

    logger.info(f"State transition: {old_state} → {new_state}")

    try:
        await self._apply_state_change(new_state)
        self._current_state = new_state

    except Exception as e:
        logger.error(
            f"Failed to transition state: {str(e)}",
            extra={
                "old_state": old_state,
                "new_state": new_state,
                "operation": "update_state"
            },
            exc_info=True
        )
        raise
```

---

## Error Context

### Required Context Fields

When logging errors, **ALWAYS** include these fields in the `extra` dictionary:

#### For API Endpoints:
```python
extra={
    "client_op_id": body.client_op_id,        # Client operation ID
    "request_id": request.headers.get("X-Request-ID"),  # Request tracking ID
    "operation": "endpoint_name",              # Operation being performed
    # Add specific context:
    "playlist_id": playlist_id,                # Resource IDs
    "track_id": track_id,
    "volume": volume,                          # Operation parameters
}
```

#### For Service Operations:
```python
extra={
    "operation": "service_method",             # Method name
    "service": "ServiceClassName",             # Service name
    # Add specific context:
    "resource_id": resource_id,
    "state": current_state,
}
```

#### For WebSocket Events:
```python
extra={
    "client_sid": sid,                         # Client session ID
    "event": "event_name",                     # Event type
    "room": room_name,                         # Target room
}
```

### Exception Information

**ALWAYS** include `exc_info=True` when logging exceptions:

```python
except Exception as e:
    logger.error(
        f"Error message: {str(e)}",
        extra={...},
        exc_info=True  # This includes full stack trace
    )
```

---

## Best Practices

### 1. Avoid Logging Sensitive Data

**Never log:**
- Passwords
- API keys / tokens
- Session tokens
- Personal identifiable information (PII)
- Credit card numbers
- Audio file content

**Safe to log:**
- User IDs (not names/emails)
- Resource IDs
- Operation names
- State transitions
- Error messages (sanitized)

### 2. Use Structured Logging

**Good:**
```python
logger.info(
    "Playlist created",
    extra={
        "playlist_id": playlist_id,
        "track_count": len(tracks),
        "duration_ms": total_duration
    }
)
```

**Bad:**
```python
logger.info(f"Created playlist {playlist_id} with {len(tracks)} tracks duration {total_duration}ms")
```

### 3. Log Levels in Production

Configure different log levels for different environments:

```python
# development.py
LOG_LEVEL = "DEBUG"

# production.py
LOG_LEVEL = "INFO"  # or "WARNING" for high-traffic services
```

### 4. Throttle High-Frequency Logs

For operations that happen frequently (e.g., position updates):

```python
self._position_log_counter += 1
if self._position_log_counter % 10 == 0:
    logger.debug(f"Broadcasting position update #{self._position_log_counter}")
```

### 5. Use Logger Names Properly

```python
# At module level
logger = logging.getLogger(__name__)  # Uses module path as logger name
```

This creates a hierarchy:
- `app.src.api.endpoints.player_api_routes`
- `app.src.services.state_event_coordinator`

---

## Examples

### Example 1: Complete API Endpoint

```python
@router.post("/playlists/{playlist_id}/play")
@handle_http_errors()
async def play_playlist(
    request: Request,
    playlist_id: str,
    body: ClientOperationRequest,
):
    """Start playing a specific playlist."""
    logger.info(f"Play playlist request received for {playlist_id}")

    try:
        # Validate playlist exists
        playlist = await playlist_service.get_playlist(playlist_id)
        if not playlist:
            logger.warning(
                f"Playlist not found: {playlist_id}",
                extra={
                    "playlist_id": playlist_id,
                    "client_op_id": body.client_op_id
                }
            )
            return UnifiedResponseService.not_found(
                message="Playlist not found",
                resource_type="playlist",
                resource_id=playlist_id
            )

        # Start playback
        result = await player_service.play_playlist(playlist_id)

        if result.get("success"):
            logger.info(f"Playlist {playlist_id} started successfully")
            await broadcasting_service.broadcast_playlist_started(playlist_id)

            return UnifiedResponseService.success(
                message="Playlist started",
                data=result.get("status"),
                server_seq=result.get("server_seq"),
                client_op_id=body.client_op_id
            )

    except Exception as e:
        logger.error(
            f"Error playing playlist: {str(e)}",
            extra={
                "playlist_id": playlist_id,
                "client_op_id": body.client_op_id,
                "request_id": request.headers.get("X-Request-ID"),
                "operation": "play_playlist",
            },
            exc_info=True
        )
        return UnifiedResponseService.internal_error(
            message="Failed to play playlist",
            operation="play_playlist"
        )
```

### Example 2: Service with Multiple Operations

```python
class PlaybackStateManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._state = "idle"

    async def transition_to_playing(self, track_id: str) -> Dict[str, Any]:
        """Transition playback state to playing."""
        old_state = self._state

        self.logger.info(f"Transitioning to playing (track: {track_id})")

        try:
            # Validate transition
            if not self._can_transition_to_playing():
                self.logger.warning(
                    f"Invalid state transition: {old_state} → playing",
                    extra={"current_state": old_state, "target_state": "playing"}
                )
                return {"success": False, "error": "invalid_transition"}

            # Perform transition
            await self._apply_playing_state(track_id)
            self._state = "playing"

            self.logger.info(f"Successfully transitioned to playing")
            return {"success": True, "state": self._state}

        except Exception as e:
            self.logger.error(
                f"Failed to transition to playing: {str(e)}",
                extra={
                    "old_state": old_state,
                    "target_state": "playing",
                    "track_id": track_id,
                    "operation": "transition_to_playing"
                },
                exc_info=True
            )
            raise
```

---

## Log Output Format

### Development
```
2025-11-09 14:30:45,123 INFO [app.src.api.endpoints.player_api_routes] Playlist abc123 started successfully
```

### Production (JSON)
```json
{
  "timestamp": "2025-11-09T14:30:45.123Z",
  "level": "INFO",
  "logger": "app.src.api.endpoints.player_api_routes",
  "message": "Playlist abc123 started successfully",
  "extra": {
    "playlist_id": "abc123",
    "client_op_id": "op_xyz789",
    "request_id": "req_abc123"
  }
}
```

---

## Monitoring and Alerts

### Recommended Alert Thresholds

| Level | Threshold | Action |
|-------|-----------|--------|
| ERROR | > 10/minute | Investigate immediately |
| WARNING | > 50/minute | Review within 1 hour |
| CRITICAL | Any occurrence | Page on-call engineer |

### Key Metrics to Track

1. **Error Rate**: Errors per minute by endpoint
2. **Exception Types**: Most common exceptions
3. **Response Times**: P50, P95, P99 latencies
4. **Client Operations**: Success/failure rates

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-09 | Initial comprehensive logging guidelines |

---

## References

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [TheOpenMusicBox API Contract](../contracts/schemas/openapi.yaml)
- [Error Handling Decorator](../back/app/src/services/error/unified_error_decorator.py)
- [Unified Response Service](../back/app/src/services/response/unified_response_service.py)
