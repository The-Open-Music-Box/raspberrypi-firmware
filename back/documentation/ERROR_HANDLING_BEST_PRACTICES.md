# Error Handling Best Practices - TheOpenMusicBox

## Overview

This document outlines the proper usage of error handling decorators and patterns in TheOpenMusicBox application, following Domain-Driven Design (DDD) principles.

## Table of Contents
1. [Error Handling Decorators](#error-handling-decorators)
2. [When to Use Each Decorator](#when-to-use-each-decorator)
3. [Return Format Consistency](#return-format-consistency)
4. [Common Pitfalls](#common-pitfalls)
5. [Examples](#examples)

## Error Handling Decorators

### 1. `@handle_errors` (Domain Layer)
- **Location**: `app.src.domain.decorators.error_handler`
- **Purpose**: Handle errors in domain layer operations
- **Returns**: Depends on `return_response` parameter
- **Usage**: Domain services, domain logic

### 2. `@handle_service_errors` (Service Layer)
- **Location**: `app.src.services.error.unified_error_decorator`
- **Purpose**: Handle errors in service layer operations that return HTTP responses
- **Returns**: `JSONResponse` via `UnifiedResponseService`
- **Usage**: HTTP endpoints, API routes

### 3. `@handle_repository_errors` (Repository Layer)
- **Location**: `app.src.services.error.unified_error_decorator`
- **Purpose**: Handle errors in repository operations
- **Returns**: Depends on implementation
- **Usage**: Database operations, repository methods

## When to Use Each Decorator

### ✅ Use `@handle_service_errors` when:
- The method is an HTTP endpoint
- The method should return a `JSONResponse`
- The method is in the routes layer
- Example:
```python
@router.post("/api/playlists")
@handle_service_errors("playlist_api")
async def create_playlist(request: Request):
    # Returns JSONResponse
    pass
```

### ❌ DON'T use `@handle_service_errors` when:
- The method returns a dictionary (Dict[str, Any])
- The method is called internally by other services
- The method is in the application service layer
- Example:
```python
# WRONG - This will break internal calls expecting a dict
@handle_service_errors("playlist_application")  # ❌ DON'T DO THIS
async def start_playlist_with_details(self, playlist_id: str) -> Dict[str, Any]:
    pass

# CORRECT - Handle errors explicitly
async def start_playlist_with_details(self, playlist_id: str) -> Dict[str, Any]:
    try:
        # ... implementation
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "error_type": "internal_error"
        }
```

### ✅ Use `@handle_errors` when:
- The method is in the domain layer
- You want flexible error handling
- The method doesn't interact with HTTP directly
- Example:
```python
@handle_errors(operation_name="calculate", component="domain.calculator")
def calculate_total(self, items: List[Item]) -> float:
    pass
```

## Return Format Consistency

### Application Service Methods
Application service methods should return consistent dictionary formats:

```python
# Success format
{
    "success": True,
    "message": "Operation completed successfully",
    "data": {...},  # Optional
    "details": {...}  # Optional
}

# Error format
{
    "success": False,
    "message": "Error description",
    "error_type": "error_category",
    "details": {...}  # Optional error details
}
```

### Alternative Format (for status-based responses)
```python
# Success format
{
    "status": "success",
    "message": "Operation completed",
    "data": {...}
}

# Error format
{
    "status": "error",
    "message": "Error description",
    "error_type": "error_category"
}
```

## Common Pitfalls

### 1. Mixing Return Types
**Problem**: Using `@handle_service_errors` on methods that should return dictionaries.

**Impact**:
- Tests fail with `KeyError: 'success'`
- Internal service calls break
- Type inconsistencies

**Solution**: Use explicit try/catch blocks for internal service methods.

### 2. Decorator Chain Issues
**Problem**: Multiple error handling decorators on the same method.

**Solution**: Use only one error handling decorator per method.

### 3. Lost Error Context
**Problem**: Generic error messages that don't provide useful information.

**Solution**: Include relevant context in error responses:
```python
except FileNotFoundError as e:
    return {
        "success": False,
        "message": f"Audio file not found: {file_path}",
        "error_type": "file_not_found",
        "details": {
            "file_path": file_path,
            "playlist_id": playlist_id,
            "error": str(e)
        }
    }
```

## Examples

### Example 1: Application Service Method (Correct)
```python
class PlaylistApplicationService:
    async def start_playlist_with_details(self, playlist_id: str, audio_service) -> Dict[str, Any]:
        """Start a playlist - returns dict for internal use."""
        try:
            # Get playlist
            playlist_data = await self._repository.get_playlist_by_id(playlist_id)
            if not playlist_data:
                return {
                    "success": False,
                    "message": f"Playlist not found: {playlist_id}",
                    "error_type": "not_found"
                }

            # Start playback
            if audio_service:
                success = audio_service.set_playlist(playlist_data)
            else:
                # Fallback
                try:
                    audio_player = self._create_audio_player()
                    success = audio_player.set_playlist(playlist_data)
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"Failed to initialize audio: {str(e)}",
                        "error_type": "audio_initialization_failure"
                    }

            return {
                "success": True,
                "message": "Playlist started successfully"
            }

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "message": "Internal error occurred",
                "error_type": "internal_error",
                "details": {"error": str(e)}
            }
```

### Example 2: HTTP Route Handler (Correct)
```python
@router.post("/api/playlists/{playlist_id}/start")
@handle_service_errors("playlist_api")
async def start_playlist(playlist_id: str, service: PlaylistApplicationService = Depends()):
    """HTTP endpoint - returns JSONResponse via decorator."""
    result = await service.start_playlist_with_details(playlist_id, None)

    if result["success"]:
        return UnifiedResponseService.success(
            message=result["message"],
            data=result.get("details")
        )
    else:
        return UnifiedResponseService.error(
            message=result["message"],
            error_type=result.get("error_type", "unknown")
        )
```

### Example 3: Domain Service (Correct)
```python
class PlaylistManager:
    @handle_errors(operation_name="validate_playlist", component="domain.playlist")
    def validate_playlist(self, playlist: Playlist) -> bool:
        """Domain logic with domain error handling."""
        if not playlist.name:
            raise ValueError("Playlist must have a name")
        if not playlist.tracks:
            raise ValueError("Playlist must have at least one track")
        return True
```

## Testing Guidelines

### Testing Error Responses
When testing methods that handle errors, verify both success and error formats:

```python
async def test_method_returns_consistent_format():
    service = MyApplicationService()

    # Test success case
    result = await service.my_method(valid_input)
    assert "success" in result or "status" in result
    if "success" in result:
        assert result["success"] is True
    else:
        assert result["status"] == "success"

    # Test error case
    result = await service.my_method(invalid_input)
    assert "success" in result or "status" in result
    if "success" in result:
        assert result["success"] is False
        assert "error_type" in result
    else:
        assert result["status"] == "error"
        assert "error_type" in result
```

## Migration Checklist

When refactoring error handling:

- [ ] Identify all methods with `@handle_service_errors`
- [ ] Check if the method is an HTTP endpoint or internal service
- [ ] Verify return type consistency (Dict vs JSONResponse)
- [ ] Update tests to match expected return format
- [ ] Add explicit error handling where decorators were removed
- [ ] Document any API changes

## Conclusion

Proper error handling is crucial for maintainable code. Follow these guidelines:

1. Use the right decorator for the right layer
2. Maintain consistent return formats within each layer
3. Provide meaningful error context
4. Test both success and error paths
5. Document expected behaviors

Remember: **Application services return dicts, HTTP endpoints return JSONResponse**.