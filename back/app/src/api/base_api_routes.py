# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Base API Routes.

Provides common functionality for API route handlers to eliminate duplication.
Follows Context7 principles with proper type safety and DDD architecture.
"""

import logging
from typing import Any, Callable, Optional, Dict
from fastapi import APIRouter

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class BaseAPIRoutes:
    """
    Base class for API route handlers.

    This class provides common functionality for API routes, including:
    - Error handling helpers
    - Service availability checks
    - Response formatting
    - Common patterns for route registration

    Subclasses should implement their own _register_routes() method.
    """

    def __init__(
        self,
        router: Optional[APIRouter] = None,
        **services
    ):
        """Initialize base API routes.

        Args:
            router: Optional FastAPI router for route registration
            **services: Named service dependencies (e.g., playlist_service, broadcasting_service)
        """
        self._router = router
        self._services = services

        # Set up logger for subclass
        self._logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def handle_system_exceptions(e: Exception) -> None:
        """Re-raise system exceptions that should not be caught.

        Extracted helper to eliminate duplication of system exception checking.
        This pattern appears in ~60+ places across API endpoints.

        Args:
            e: The exception to check

        Raises:
            The exception if it's a system exception
        """
        if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
            raise

    def check_service_available(
        self,
        service_name: str,
        service_instance: Any,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Check if a service is available and return error response if not.

        Extracted helper to eliminate duplication of service availability checks.
        This pattern appears in ~30+ places across API endpoints.

        Args:
            service_name: Name of the service for error messages
            service_instance: The service instance to check
            error_message: Optional custom error message

        Returns:
            UnifiedResponseService error response if service unavailable, None otherwise
        """
        if not service_instance:
            message = error_message or f"{service_name} service not available"
            return UnifiedResponseService.service_unavailable(
                service=service_name,
                message=message
            )
        return None

    def handle_endpoint_error(
        self,
        error: Exception,
        operation: str,
        message: Optional[str] = None,
        **extra_context
    ) -> Dict[str, Any]:
        """Handle errors in API endpoints with consistent logging and response.

        Extracted helper to eliminate duplication of error handling logic.
        This pattern appears in ~60+ places across API endpoints.

        Args:
            error: The exception that occurred
            operation: Name of the operation for logging
            message: Optional custom error message
            **extra_context: Additional context for logging

        Returns:
            UnifiedResponseService error response
        """
        # Re-raise system exceptions first
        self.handle_system_exceptions(error)

        # Log the error with context
        error_msg = f"Error in {operation}: {str(error)}"
        if extra_context:
            self._logger.error(error_msg, extra=extra_context, exc_info=True)
        else:
            self._logger.error(error_msg, exc_info=True)

        # Return error response
        return UnifiedResponseService.internal_error(
            message=message or f"Failed to {operation}",
            operation=operation
        )

    def log_operation(
        self,
        operation: str,
        level: str = "info",
        **context
    ) -> None:
        """Log an API operation with consistent formatting.

        Helper to provide consistent logging across API endpoints.

        Args:
            operation: Description of the operation
            level: Log level (info, debug, warning, error)
            **context: Additional context for logging
        """
        log_method = getattr(self._logger, level, self._logger.info)
        if context:
            log_method(f"{operation}", extra=context)
        else:
            log_method(operation)

    def get_service(self, service_name: str) -> Any:
        """Get a named service from the services dict.

        Helper for accessing injected services.

        Args:
            service_name: Name of the service to retrieve

        Returns:
            The service instance or None if not found
        """
        return self._services.get(service_name)

    def register_route_with_error_handling(
        self,
        router: APIRouter,
        method: str,
        path: str,
        handler: Callable,
        **route_kwargs
    ) -> None:
        """Register a route with automatic error handling decorator.

        Helper to eliminate duplication of route registration pattern.

        Args:
            router: FastAPI router to register on
            method: HTTP method (get, post, put, delete, etc.)
            path: Route path
            handler: Route handler function
            **route_kwargs: Additional route configuration (status_code, tags, etc.)
        """
        # Get the route registration method (e.g., router.post, router.get)
        register_method = getattr(router, method.lower())

        # Register with error handling decorator
        decorated_handler = handle_http_errors()(handler)
        register_method(path, **route_kwargs)(decorated_handler)
