# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Domain Layer Error Handler Decorator

Pure domain error handling without infrastructure dependencies.
"""

import asyncio
import functools
import traceback
from typing import Callable, Any, Optional, Dict
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


def handle_domain_errors(
    operation_name: Optional[str] = None,
    component: Optional[str] = None,
    log_level: int = logging.ERROR,
    include_trace: bool = False,
    reraise: bool = True,
    default_return: Any = None,
) -> Callable:
    """
    Pure domain layer error handler decorator.

    Args:
        operation_name: Name of the operation (defaults to function name)
        component: Component name (defaults to module name)
        log_level: Logging level for errors
        include_trace: Include stack trace in logs
        reraise: Whether to re-raise the exception after logging
        default_return: Default value to return on error (if not reraising)

    Returns:
        Decorated function with error handling
    """

    def decorator(func: Callable) -> Callable:
        func_component = component or getattr(func, "__module__", "unknown")
        func_operation = operation_name or func.__name__

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    _handle_error(e, func_operation, func_component, log_level, include_trace)
                    if reraise:
                        raise
                    return default_return
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    _handle_error(e, func_operation, func_component, log_level, include_trace)
                    if reraise:
                        raise
                    return default_return
            return sync_wrapper

    return decorator


def _handle_error(
    error: Exception,
    operation: str,
    component: str,
    log_level: int,
    include_trace: bool
) -> None:
    """Handle and log domain errors."""
    log_message = f"Domain error in {component}.{operation}: {str(error)}"
    extra_data = {
        "operation": operation,
        "component": component,
        "error_type": type(error).__name__,
        "timestamp": datetime.now().isoformat(),
    }

    if include_trace:
        extra_data["traceback"] = traceback.format_exc()

    logger.log(log_level, log_message, extra=extra_data)


# Alias for backward compatibility
handle_errors = handle_domain_errors
