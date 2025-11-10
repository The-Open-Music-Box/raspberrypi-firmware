# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
API Decorators Module

Provides decorators for FastAPI endpoint common patterns:
- Rate limiting checks
- Operation tracking (client_op_id, server_seq)
- Request/response logging
- Service dependency injection

These decorators eliminate repetitive code in API route handlers.
"""

import functools
import logging
from typing import Callable, Optional, Any
from fastapi import Request

from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


def with_rate_limiting(
    service_attr: str = "_operations_service",
    enabled_check: Optional[Callable] = None
) -> Callable:
    """
    Decorator to handle rate limiting checks for API endpoints.

    Eliminates the repetitive rate limiting pattern:
    ```python
    if self._operations_service:
        rate_check = await self._operations_service.check_rate_limit_use_case(request)
        if not rate_check.get("allowed", True):
            return UnifiedResponseService.error(...)
    ```

    Usage:
    ```python
    @with_rate_limiting()
    async def my_endpoint(self, request: Request, ...):
        # Rate limiting is automatically checked
        # Function only executes if rate limit allows
        pass
    ```

    Args:
        service_attr: Name of the attribute containing the operations service.
                     Default is "_operations_service".
        enabled_check: Optional callable to check if rate limiting should be enabled.
                      If None, checks if service_attr exists and is not None.

    Returns:
        Decorated function with automatic rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract self and request from args/kwargs
            self_obj = None
            request_obj = None

            # Get self from args[0] (if it's a method)
            if args and hasattr(args[0], service_attr):
                self_obj = args[0]

            # Find request in args or kwargs
            for arg in args:
                if isinstance(arg, Request):
                    request_obj = arg
                    break
            if not request_obj and "request" in kwargs:
                request_obj = kwargs["request"]

            # Check if rate limiting should be applied
            operations_service = None
            if self_obj:
                operations_service = getattr(self_obj, service_attr, None)

            should_rate_limit = (
                operations_service is not None
                if enabled_check is None
                else enabled_check(self_obj)
            )

            if should_rate_limit and operations_service and request_obj:
                # Perform rate limit check
                try:
                    rate_check = await operations_service.check_rate_limit_use_case(request_obj)
                    if not rate_check.get("allowed", True):
                        logger.warning(
                            f"Rate limit exceeded for {func.__name__}: "
                            f"{rate_check.get('message', 'Too many requests')}"
                        )
                        return UnifiedResponseService.error(
                            message=rate_check.get("message", "Too many requests"),
                            error_type="rate_limit_error",
                            status_code=429
                        )
                except Exception as e:
                    # Log but don't block on rate limiting errors
                    logger.error(f"Rate limiting check failed for {func.__name__}: {str(e)}")
                    # Continue to execute the function

            # Execute the wrapped function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_operation_tracking(
    extract_client_op_id: Optional[Callable] = None,
    extract_server_seq: Optional[Callable] = None,
) -> Callable:
    """
    Decorator to track operations with client_op_id and server_seq.

    Automatically extracts and logs operation identifiers for tracing.

    Usage:
    ```python
    @with_operation_tracking()
    async def my_endpoint(self, request: Request, body: RequestModel, ...):
        # Operation is automatically tracked
        pass
    ```

    Args:
        extract_client_op_id: Custom function to extract client_op_id from args/kwargs
        extract_server_seq: Custom function to extract server_seq from result

    Returns:
        Decorated function with operation tracking
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract client_op_id
            client_op_id = None
            if extract_client_op_id:
                client_op_id = extract_client_op_id(args, kwargs)
            else:
                # Try to extract from body parameter
                if "body" in kwargs:
                    body = kwargs["body"]
                    if hasattr(body, "client_op_id"):
                        client_op_id = body.client_op_id
                    elif isinstance(body, dict):
                        client_op_id = body.get("client_op_id")

            # Log operation start
            if client_op_id:
                logger.debug(
                    f"Operation {func.__name__} started with client_op_id={client_op_id}"
                )

            # Execute function
            result = await func(*args, **kwargs)

            # Extract server_seq from result if available
            server_seq = None
            if extract_server_seq:
                server_seq = extract_server_seq(result)
            elif isinstance(result, dict):
                server_seq = result.get("server_seq")

            # Log operation completion
            if client_op_id or server_seq:
                logger.debug(
                    f"Operation {func.__name__} completed: "
                    f"client_op_id={client_op_id}, server_seq={server_seq}"
                )

            return result

        return wrapper

    return decorator


def with_request_logging(
    log_request: bool = True,
    log_response: bool = True,
    log_level: int = logging.DEBUG,
    include_body: bool = False,
) -> Callable:
    """
    Decorator to log API requests and responses.

    Usage:
    ```python
    @with_request_logging(include_body=True)
    async def my_endpoint(self, request: Request, ...):
        # Requests and responses are automatically logged
        pass
    ```

    Args:
        log_request: Whether to log incoming requests
        log_response: Whether to log outgoing responses
        log_level: Logging level to use
        include_body: Whether to include request/response body in logs

    Returns:
        Decorated function with request/response logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request_obj = None
            for arg in args:
                if isinstance(arg, Request):
                    request_obj = arg
                    break
            if not request_obj and "request" in kwargs:
                request_obj = kwargs["request"]

            # Log request
            if log_request and request_obj:
                log_data = {
                    "endpoint": func.__name__,
                    "method": request_obj.method,
                    "path": str(request_obj.url.path),
                }
                if include_body and "body" in kwargs:
                    log_data["body"] = str(kwargs["body"])

                logger.log(
                    log_level,
                    f"API Request: {log_data['method']} {log_data['path']} -> {func.__name__}",
                    extra=log_data
                )

            # Execute function
            result = await func(*args, **kwargs)

            # Log response
            if log_response:
                log_data = {
                    "endpoint": func.__name__,
                    "status": "success" if result else "error",
                }
                if include_body and isinstance(result, dict):
                    log_data["response_status"] = result.get("status")

                logger.log(
                    log_level,
                    f"API Response: {func.__name__} -> {log_data['status']}",
                    extra=log_data
                )

            return result

        return wrapper

    return decorator


def combine_decorators(*decorators: Callable) -> Callable:
    """
    Helper to combine multiple decorators into one.

    Usage:
    ```python
    api_endpoint = combine_decorators(
        with_rate_limiting(),
        with_operation_tracking(),
        with_request_logging()
    )

    @api_endpoint
    async def my_endpoint(self, request: Request, ...):
        pass
    ```

    Args:
        *decorators: Decorators to combine

    Returns:
        Combined decorator
    """
    def combined_decorator(func: Callable) -> Callable:
        for decorator in reversed(decorators):
            func = decorator(func)
        return func

    return combined_decorator


# Pre-configured decorator combinations for common patterns
standard_api_endpoint = combine_decorators(
    with_rate_limiting(),
    with_operation_tracking(),
)

logged_api_endpoint = combine_decorators(
    with_rate_limiting(),
    with_operation_tracking(),
    with_request_logging(),
)
