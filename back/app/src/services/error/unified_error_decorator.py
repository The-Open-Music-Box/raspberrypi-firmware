# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified Error Decorator

This module provides decorators to automatically handle errors and eliminate
the 600+ duplicated try/catch blocks across the application.
"""

import asyncio
import functools
import traceback
from typing import Callable, Any, Optional, Dict, Union
from datetime import datetime

from fastapi import HTTPException
import logging
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class ErrorContext:
    """Context information for error handling."""

    def __init__(
        self,
        operation: str = None,
        component: str = None,
        client_op_id: str = None,
        user_friendly: bool = True,
        log_level: Any = logging.ERROR,
        include_trace: bool = False,
    ):
        self.operation = operation
        self.component = component
        self.client_op_id = client_op_id
        self.user_friendly = user_friendly
        self.log_level = log_level
        self.include_trace = include_trace
        self.timestamp = datetime.now().isoformat()


def handle_errors(
    operation_name: Optional[str] = None,
    component: Optional[str] = None,
    return_response: bool = True,
    log_level: Any = logging.ERROR,
    include_trace: bool = False,
    custom_error_map: Optional[Dict[type, str]] = None,
) -> Callable:
    """
    Décorateur pour gestion automatique des erreurs.

    Remplace les 600+ try/catch blocks avec:
    @handle_errors("operation_name")

    Args:
        operation_name: Nom de l'opération (déduit du nom de fonction si None)
        component: Nom du composant (déduit du module si None)
        return_response: Retourner UnifiedResponseService.error() ou re-raise
        log_level: Niveau de log pour les erreurs
        include_trace: Inclure la stack trace dans la réponse
        custom_error_map: Mapping custom d'exceptions vers messages

    Returns:
        Decorated function with automatic error handling
    """

    def decorator(func: Callable) -> Callable:
        # Determine component from module if not provided
        func_component = component or getattr(func, "__module__", "unknown")
        func_operation = operation_name or func.__name__

        # Build custom error mapping
        error_map = {
            ValueError: "Invalid input parameters",
            KeyError: "Required field missing",
            FileNotFoundError: "Required file not found",
            PermissionError: "Access denied",
            ConnectionError: "Service connection failed",
            TimeoutError: "Operation timed out",
            # Add custom mappings
            **(custom_error_map or {}),
        }

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _execute_with_error_handling(
                    func,
                    args,
                    kwargs,
                    func_operation,
                    func_component,
                    return_response,
                    log_level,
                    include_trace,
                    error_map,
                )

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _execute_sync_with_error_handling(
                    func,
                    args,
                    kwargs,
                    func_operation,
                    func_component,
                    return_response,
                    log_level,
                    include_trace,
                    error_map,
                )

            return sync_wrapper

    return decorator


def _to_std_level(level: Any) -> int:
    """Convert a custom LogLevel enum or string/int to stdlib logging level."""
    try:
        # Enum with .value like 'error'
        name = getattr(level, 'value', None)
        if isinstance(name, str):
            return getattr(logging, name.upper(), logging.ERROR)
        # If string provided directly
        if isinstance(level, str):
            return getattr(logging, level.upper(), logging.ERROR)
        # If already an int
        if isinstance(level, int):
            return level
    except Exception as e:
        # Re-raise system exceptions immediately
        if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
            raise
        pass
    return logging.ERROR


async def _execute_with_error_handling(
    func: Callable,
    args: tuple,
    kwargs: dict,
    operation: str,
    component: str,
    return_response: bool,
    log_level: Any,
    include_trace: bool,
    error_map: Dict[type, str],
) -> Any:
    """Execute async function with error handling."""
    try:
        return await func(*args, **kwargs)
    except HTTPException:
        # Re-raise HTTP exceptions (they're already handled)
        raise
    except Exception as e:
        if return_response:
            return _handle_caught_exception(
                e, operation, component, return_response, log_level, include_trace, error_map, kwargs
            )
        else:
            # Log and re-raise for domain/repository layers
            _handle_caught_exception(
                e, operation, component, return_response, log_level, include_trace, error_map, kwargs
            )
            # _handle_caught_exception will raise the exception when return_response=False


def _execute_sync_with_error_handling(
    func: Callable,
    args: tuple,
    kwargs: dict,
    operation: str,
    component: str,
    return_response: bool,
    log_level: Any,
    include_trace: bool,
    error_map: Dict[type, str],
) -> Any:
    """Execute sync function with error handling."""
    try:
        return func(*args, **kwargs)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        if return_response:
            return _handle_caught_exception(
                e, operation, component, return_response, log_level, include_trace, error_map, kwargs
            )
        else:
            # Log and re-raise for domain/repository layers
            _handle_caught_exception(
                e, operation, component, return_response, log_level, include_trace, error_map, kwargs
            )
            # _handle_caught_exception will raise the exception when return_response=False


def _handle_caught_exception(
    error: Exception,
    operation: str,
    component: str,
    return_response: bool,
    log_level: Any,
    include_trace: bool,
    error_map: Dict[type, str],
    kwargs: dict,
) -> Any:
    """Handle caught exception with unified logic."""
    # Extract client_op_id if available
    client_op_id = None
    if "client_op_id" in kwargs:
        client_op_id = kwargs["client_op_id"]
    elif "body" in kwargs and isinstance(kwargs["body"], dict):
        client_op_id = kwargs["body"].get("client_op_id")
    elif len(kwargs) > 0:
        # Try to find client_op_id in any dict parameter
        for value in kwargs.values():
            if isinstance(value, dict) and "client_op_id" in value:
                client_op_id = value["client_op_id"]
                break

    # Get user-friendly error message
    error_type = type(error)
    user_message = error_map.get(error_type, f"Operation failed: {operation}")

    # Create error context for detailed logging
    error_context = ErrorContext(
        operation=operation,
        component=component,
        client_op_id=client_op_id,
        log_level=log_level,
        include_trace=include_trace,
    )

    # Log the error with full context
    log_message = f"❌ Error in {component}.{operation}: {str(error)}"
    extra_data = {
        "operation": operation,
        "component": component,
        "error_type": error_type.__name__,
        "client_op_id": client_op_id,
    }

    if include_trace:
        extra_data["traceback"] = traceback.format_exc()

    logger.log(_to_std_level(log_level), log_message, extra=extra_data)

    if return_response:
        # Return UnifiedResponseService error response
        return UnifiedResponseService.internal_error(
            message=user_message,
            operation=operation,
            client_op_id=client_op_id,
            trace=include_trace,
        )
    else:
        # Re-raise the original exception
        raise


def handle_http_errors(
    default_status: int = 500, error_mappings: Optional[Dict[type, int]] = None
) -> Callable:
    """
    Décorateur spécialisé pour endpoints HTTP.

    Args:
        default_status: Status code par défaut pour erreurs non mappées
        error_mappings: Mapping d'exceptions vers status codes HTTP

    Returns:
        Decorator for HTTP endpoints
    """
    mappings = error_mappings or {
        ValueError: 400,
        KeyError: 400,
        FileNotFoundError: 404,
        PermissionError: 403,
        ConnectionError: 503,
        TimeoutError: 504,
    }

    def decorator(func: Callable) -> Callable:
        @handle_errors(
            operation_name=func.__name__,
            return_response=False,  # Let HTTP exception handling work
            include_trace=False,
        )
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                # Convert to appropriate HTTP status
                status_code = mappings.get(type(e), default_status)
                raise HTTPException(status_code=status_code, detail=str(e))

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                # Convert to appropriate HTTP status
                status_code = mappings.get(type(e), default_status)
                raise HTTPException(status_code=status_code, detail=str(e))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def handle_validation_errors(validation_context: str = "api") -> Callable:
    """
    Décorateur spécialisé pour validation d'entrées.

    Args:
        validation_context: Context de validation pour messages d'erreur

    Returns:
        Decorator for validation functions
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                # Return validation error response
                return UnifiedResponseService.validation_error(
                    errors=[{"message": str(e)}],
                    message=f"Validation failed in {validation_context}",
                )
            except Exception as e:
                logger.error(
                    f"Unexpected validation error in {validation_context}: {str(e)}"
                )
                return UnifiedResponseService.validation_error(
                    errors=[{"message": "Validation error occurred"}],
                    message=f"Validation failed in {validation_context}",
                )

        return wrapper

    return decorator


def handle_repository_errors(entity_name: str = "entity") -> Callable:
    """
    Décorateur spécialisé pour opérations repository.

    Utilise l'architecture unifiée avec return_response=False pour éviter JSONResponse.
    Les repositories doivent lever des exceptions, pas retourner des réponses HTTP.

    Args:
        entity_name: Nom de l'entité pour messages d'erreur

    Returns:
        Decorator for repository methods
    """

    def decorator(func: Callable) -> Callable:
        return handle_errors(
            component=f"repository_{entity_name}",
            operation_name=func.__name__,
            log_level=logging.ERROR,
            include_trace=True,  # Repository errors need stack trace for debugging
            return_response=False,  # CRITICAL: Ne pas retourner JSONResponse
            custom_error_map={
                FileNotFoundError: f"{entity_name} not found",
                PermissionError: f"Access denied to {entity_name}",
                ValueError: f"Invalid {entity_name} data",
                KeyError: f"{entity_name} key not found",
                TypeError: f"Invalid {entity_name} type",
            },
        )(func)

    return decorator


def handle_infrastructure_errors(component_name: str = "infrastructure") -> Callable:
    """
    Décorateur spécialisé pour couche infrastructure.

    Infrastructure ne doit PAS retourner JSONResponse, seulement lever des exceptions
    pour les couches supérieures (domaine/application).

    Args:
        component_name: Nom du composant infrastructure

    Returns:
        Decorator for infrastructure methods
    """

    def decorator(func: Callable) -> Callable:
        return handle_errors(
            component=f"infrastructure_{component_name}",
            operation_name=func.__name__,
            log_level=logging.ERROR,
            include_trace=True,  # Infrastructure errors need debugging info
            return_response=False,  # CRITICAL: Ne pas retourner JSONResponse
            custom_error_map={
                ConnectionError: f"Connection failed in {component_name}",
                TimeoutError: f"Timeout in {component_name}",
                PermissionError: f"Permission denied in {component_name}",
                FileNotFoundError: f"Resource not found in {component_name}",
                ValueError: f"Invalid value in {component_name}",
            },
        )(func)

    return decorator


def handle_service_errors(service_name: str) -> Callable:
    """
    Décorateur spécialisé pour services d'application.

    Args:
        service_name: Nom du service pour logging/tracking

    Returns:
        Decorator for service methods
    """

    def decorator(func: Callable) -> Callable:
        @handle_errors(
            component=service_name,
            operation_name=func.__name__,
            log_level=logging.ERROR,
            include_trace=False,
            return_response=False,  # Don't return JSONResponse, let method return dict
        )
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Return error dict instead of JSONResponse for internal service calls
                return {
                    "status": "error",
                    "message": str(e),
                    "error_type": type(e).__name__,
                    "operation": func.__name__,
                }

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Return error dict instead of JSONResponse for internal service calls
                return {
                    "status": "error",
                    "message": str(e),
                    "error_type": type(e).__name__,
                    "operation": func.__name__,
                }

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class ErrorTracker:
    """Track error patterns and statistics."""

    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.max_history = 1000

    def track_error(self, error_type: str, operation: str, component: str):
        """Track an error occurrence."""
        key = f"{component}.{operation}.{error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

        self.error_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "operation": operation,
                "component": component,
            }
        )

        # Trim history if too long
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history :]

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": len(set(entry["error_type"] for entry in self.error_history)),
            "top_errors": sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "recent_errors": self.error_history[-10:],
        }


# Removed Global Instance
# error_tracker global instance has been removed in favor of dependency injection
# Use: container.get("error_tracker")
# Migration completed: All code now uses DI
