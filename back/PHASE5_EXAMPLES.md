# Phase 5 Refactoring - Before/After Examples

This document provides concrete before/after examples of the refactoring work completed in Phase 5.

---

## Example 1: Enhanced Error Logging in NFC API Routes

### Before (nfc_api_routes.py - associate_tag_with_playlist)

```python
except Exception as e:
    logger.error(f"Error associating NFC tag: {str(e)}", exc_info=True)
    return UnifiedResponseService.internal_error(
        message="Failed to associate NFC tag",
        operation="associate_tag_with_playlist"
    )
```

**Issues:**
- Generic error message without context
- No request tracing information
- Missing operation-specific details
- Difficult to debug in production

### After (nfc_api_routes.py - associate_tag_with_playlist)

```python
except Exception as e:
    logger.error(
        f"Error in associate_tag_with_playlist: {str(e)}",
        extra={
            "client_op_id": body.client_op_id if hasattr(body, 'client_op_id') else None,
            "request_id": request.headers.get("X-Request-ID") if request else None,
            "operation": "associate_tag_with_playlist",
            "playlist_id": body.playlist_id if hasattr(body, 'playlist_id') else None,
            "tag_id": body.tag_id if hasattr(body, 'tag_id') else None,
        },
        exc_info=True
    )
    return UnifiedResponseService.internal_error(
        message="Failed to associate NFC tag",
        operation="associate_tag_with_playlist"
    )
```

**Improvements:**
✅ Standardized error message format with operation name
✅ Client operation ID for request tracing
✅ Request ID from HTTP header
✅ Operation-specific context (playlist_id, tag_id)
✅ Defensive programming with hasattr() checks
✅ Structured logging with extra dictionary

**Production Benefit:**
When an error occurs, logs now show:
```
ERROR: Error in associate_tag_with_playlist: Connection timeout
  client_op_id: op-1234-5678
  request_id: req-abc-def-789
  operation: associate_tag_with_playlist
  playlist_id: playlist-42
  tag_id: tag-nfc-001
  [Full stack trace]
```

This enables rapid troubleshooting by correlating errors with specific requests.

---

## Example 2: Enhanced Error Logging in Playlist API

### Before (playlist_write_api.py - create_playlist)

```python
except Exception as e:
    if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
        raise
    logger.error(f"Error creating playlist: {str(e)}", extra={"traceback": True})
    return UnifiedResponseService.internal_error(
        message="Failed to create playlist",
        operation="create_playlist",
        client_op_id=body.get("client_op_id") if isinstance(body, dict) else None,
    )
```

**Issues:**
- Inconsistent extra field (using "traceback" instead of standard pattern)
- Missing operation name in extra context
- Missing playlist title for debugging
- Less structured than standard pattern

### After (playlist_write_api.py - create_playlist)

```python
except Exception as e:
    if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
        raise
    logger.error(
        f"Error in create_playlist: {str(e)}",
        extra={
            "client_op_id": body.get("client_op_id") if isinstance(body, dict) else None,
            "operation": "create_playlist",
            "title": body.get("title") if isinstance(body, dict) else None,
        },
        exc_info=True
    )
    return UnifiedResponseService.internal_error(
        message="Failed to create playlist",
        operation="create_playlist",
        client_op_id=body.get("client_op_id") if isinstance(body, dict) else None,
    )
```

**Improvements:**
✅ Consistent with standard error logging pattern
✅ Operation name in extra context for filtering
✅ Playlist title for debugging context
✅ Standard exc_info=True instead of custom traceback field
✅ Defensive dict type checking

---

## Example 3: Complex Conditional Extraction

### Before (nfc_handlers.py - handle_override_nfc_tag)

```python
@self.sio.on("override_nfc_tag")
@handle_http_errors()
async def handle_override_nfc_tag(sid: str, data: Dict[str, Any]) -> None:
    playlist_id = data.get("playlist_id")
    tag_id = data.get("tag_id")
    client_op_id = data.get("client_op_id")
    if not playlist_id:
        raise ValueError("playlist_id is required")

    logger.info(f"Overriding NFC tag {tag_id} for playlist {playlist_id} from client {sid}")

    # Get NFC service
    nfc_service = self._get_nfc_service()

    # Start association in override mode (NEW: pass override_mode=True)
    result = await nfc_service.start_association_use_case(
        playlist_id,
        timeout_seconds=60,
        override_mode=True,  # Force association even if tag already associated
    )

    # Get session info
    session = result.get("session", {})
    session_id = session.get("session_id")
    timeout_at = session.get("timeout_at")

    # Calculate expires_at timestamp for frontend countdown
    if timeout_at:
        expires_at = datetime.fromisoformat(
            timeout_at.replace("Z", "+00:00")
        ).timestamp()
    else:
        expires_at = time.time() + 60

    # If tag_id is provided, immediately process it (no need to scan again)
    if tag_id:
        logger.info(f"Processing saved tag {tag_id} immediately for override")
        tag_identifier = TagIdentifier(uid=tag_id)
        await nfc_service._handle_tag_detection(tag_identifier)
        logger.info(f"Override completed automatically for tag {tag_id}")
    else:
        # No tag_id provided, emit waiting state (old behavior)
        await self.sio.emit(
            "nfc_association_state",
            {
                "state": "waiting",
                "playlist_id": playlist_id,
                "session_id": session_id,
                "expires_at": expires_at,
                "override_mode": True,
                "message": "Place NFC tag to override existing association",
                "server_seq": self.state_manager.get_global_sequence(),
            },
            room=sid,
        )

    # Send acknowledgment
    if client_op_id:
        await self.state_manager.send_acknowledgment(
            client_op_id,
            True,
            {
                "session_id": session_id,
                "playlist_id": playlist_id,
                "override": True,
                "tag_id": tag_id,
                "auto_processed": tag_id is not None,
            },
        )

    logger.info(f"NFC tag override started for playlist {playlist_id} (session: {session_id})")
```

**Issues:**
- Handler method is very long (~50 lines)
- Complex nested conditionals make flow hard to follow
- Multiple responsibilities (session creation, tag processing, state emission, acknowledgment)
- Difficult to test individual pieces
- Timestamp calculation logic embedded in handler

### After (nfc_handlers.py - handle_override_nfc_tag)

```python
@self.sio.on("override_nfc_tag")
@handle_http_errors()
async def handle_override_nfc_tag(sid: str, data: Dict[str, Any]) -> None:
    """Handle NFC tag override via WebSocket.

    [Full docstring...]
    """
    try:
        playlist_id = data.get("playlist_id")
        tag_id = data.get("tag_id")
        client_op_id = data.get("client_op_id")
        if not playlist_id:
            raise ValueError("playlist_id is required")

        logger.info(
            f"Overriding NFC tag {tag_id} for playlist {playlist_id} from client {sid}"
        )

        # Get NFC service
        nfc_service = self._get_nfc_service()

        # Start override session and process tag if provided
        session_id = await self._start_override_session(
            nfc_service, playlist_id, tag_id, sid, client_op_id
        )

        logger.info(
            f"NFC tag override started for playlist {playlist_id} (session: {session_id})"
        )
    except Exception as e:
        logger.error(
            f"Error in handle_override_nfc_tag: {str(e)}",
            extra={
                "sid": sid,
                "client_op_id": data.get("client_op_id") if isinstance(data, dict) else None,
                "playlist_id": data.get("playlist_id") if isinstance(data, dict) else None,
                "tag_id": data.get("tag_id") if isinstance(data, dict) else None,
                "operation": "override_nfc_tag",
            },
            exc_info=True
        )
        raise
```

**New Helper Method:**

```python
async def _start_override_session(
    self,
    nfc_service: Any,
    playlist_id: str,
    tag_id: Optional[str],
    sid: str,
    client_op_id: Optional[str],
) -> str:
    """Start an NFC override session and optionally process a tag immediately.

    Args:
        nfc_service: The NFC application service
        playlist_id: The playlist to associate
        tag_id: Optional tag identifier to process immediately
        sid: The client session identifier
        client_op_id: Optional client operation ID for acknowledgment

    Returns:
        The session ID of the created override session

    Side Effects:
        - Starts an NFC association session in override mode
        - If tag_id provided: Processes the tag immediately
        - If no tag_id: Emits waiting state to client
        - Sends acknowledgment if client_op_id provided
    """
    # Start association in override mode
    result = await nfc_service.start_association_use_case(
        playlist_id,
        timeout_seconds=60,
        override_mode=True,
    )

    # Get session info
    session = result.get("session", {})
    session_id = session.get("session_id")
    timeout_at = session.get("timeout_at")

    # Calculate expires_at timestamp for frontend countdown
    expires_at = self._calculate_expires_at(timeout_at)

    # If tag_id is provided, immediately process it
    if tag_id:
        await self._process_tag_override(nfc_service, tag_id, sid)
    else:
        # No tag_id provided, emit waiting state
        await self._emit_waiting_state(
            sid, playlist_id, session_id, expires_at
        )

    # Send acknowledgment
    if client_op_id:
        await self.state_manager.send_acknowledgment(
            client_op_id,
            True,
            {
                "session_id": session_id,
                "playlist_id": playlist_id,
                "override": True,
                "tag_id": tag_id,
                "auto_processed": tag_id is not None,
            },
        )

    return session_id
```

**Improvements:**
✅ Handler reduced from ~50 lines to ~20 lines
✅ Clear separation of concerns
✅ Helper method is independently testable
✅ Comprehensive docstring documents behavior
✅ Enhanced error logging added to handler
✅ Single Responsibility Principle applied
✅ Complex conditional logic isolated in helper
✅ Improved code readability

**Testing Benefit:**
Can now test helper method in isolation:
```python
async def test_start_override_session_with_tag_id():
    # Test immediate tag processing
    session_id = await handler._start_override_session(
        nfc_service, playlist_id, tag_id="test-tag", sid="test-sid", client_op_id=None
    )
    assert session_id is not None
    nfc_service._handle_tag_detection.assert_called_once()

async def test_start_override_session_without_tag_id():
    # Test waiting state emission
    session_id = await handler._start_override_session(
        nfc_service, playlist_id, tag_id=None, sid="test-sid", client_op_id=None
    )
    assert session_id is not None
    handler.sio.emit.assert_called_once_with("nfc_association_state", ...)
```

---

## Example 4: WebSocket Handler Error Logging

### Before (nfc_handlers.py - handle_start_nfc_link)

```python
@self.sio.on("start_nfc_link")
@handle_http_errors()
async def handle_start_nfc_link(sid: str, data: Dict[str, Any]) -> None:
    playlist_id = data.get("playlist_id")
    client_op_id = data.get("client_op_id")
    if not playlist_id:
        raise ValueError("playlist_id is required")

    logger.info(f"Starting NFC association for playlist {playlist_id} from client {sid}")

    nfc_service = self._get_nfc_service()
    result = await nfc_service.start_association_use_case(playlist_id)

    await self.sio.emit(
        "nfc_association_state",
        {
            "state": "activated",
            "playlist_id": playlist_id,
            "expires_at": result.get("expires_at"),
            "server_seq": self.state_manager.get_global_sequence(),
        },
        room=sid,
    )

    if client_op_id:
        await self.state_manager.send_acknowledgment(
            client_op_id,
            True,
            {"assoc_id": result.get("assoc_id"), "playlist_id": playlist_id},
        )

    logger.info(f"NFC association started successfully for playlist {playlist_id}")
```

**Issues:**
- No exception handling in handler itself
- Relies entirely on decorator for error handling
- If error occurs, no contextual logging
- No operation-specific error details

### After (nfc_handlers.py - handle_start_nfc_link)

```python
@self.sio.on("start_nfc_link")
@handle_http_errors()
async def handle_start_nfc_link(sid: str, data: Dict[str, Any]) -> None:
    try:
        playlist_id = data.get("playlist_id")
        client_op_id = data.get("client_op_id")
        if not playlist_id:
            raise ValueError("playlist_id is required")

        logger.info(
            f"Starting NFC association for playlist {playlist_id} from client {sid}"
        )

        nfc_service = self._get_nfc_service()
        result = await nfc_service.start_association_use_case(playlist_id)

        await self.sio.emit(
            "nfc_association_state",
            {
                "state": "activated",
                "playlist_id": playlist_id,
                "expires_at": result.get("expires_at"),
                "server_seq": self.state_manager.get_global_sequence(),
            },
            room=sid,
        )

        if client_op_id:
            await self.state_manager.send_acknowledgment(
                client_op_id,
                True,
                {"assoc_id": result.get("assoc_id"), "playlist_id": playlist_id},
            )

        logger.info(
            f"NFC association started successfully for playlist {playlist_id}"
        )
    except Exception as e:
        logger.error(
            f"Error in handle_start_nfc_link: {str(e)}",
            extra={
                "sid": sid,
                "client_op_id": data.get("client_op_id") if isinstance(data, dict) else None,
                "playlist_id": data.get("playlist_id") if isinstance(data, dict) else None,
                "operation": "start_nfc_link",
            },
            exc_info=True
        )
        raise
```

**Improvements:**
✅ Explicit try/except block for better control
✅ Rich contextual logging on errors
✅ WebSocket session ID (sid) captured
✅ Operation name for log filtering
✅ Still re-raises exception for decorator to handle
✅ Defensive data access with isinstance checks

---

## Summary of Pattern Consistency

All refactored code now follows these consistent patterns:

### Error Logging Pattern
```python
logger.error(
    f"Error in {operation_name}: {str(e)}",
    extra={
        "client_op_id": ...,
        "request_id": ...,
        "operation": "operation_name",
        # Operation-specific context
    },
    exc_info=True
)
```

### Defensive Access Pattern
```python
# For Pydantic models
body.field_name if hasattr(body, 'field_name') else None

# For dictionaries
data.get("field_name") if isinstance(data, dict) else None

# For request headers
request.headers.get("X-Request-ID") if request else None
```

### Helper Method Pattern
```python
async def _helper_method_name(
    self,
    param1: Type1,
    param2: Type2,
) -> ReturnType:
    """One-line summary.

    Detailed description of what this helper does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Side Effects:
        - List of side effects
        - Another side effect

    Raises:
        ExceptionType: When this exception occurs
    """
    # Implementation
    ...
```

---

**Document Generated:** 2025-11-09
**Project:** TheOpenMusicBox Phase 5 Refactoring
