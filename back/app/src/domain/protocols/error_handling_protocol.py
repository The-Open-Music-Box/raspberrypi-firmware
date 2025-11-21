# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Error Handling Protocol.

Defines the interface for error handling decorators and services.
"""

from typing import Protocol, Callable, Dict, Optional, Any


class ErrorHandlerProtocol(Protocol):
    """Protocol for error handling decorators."""

    def __call__(
        self,
        operation_name: Optional[str] = None,
        component: Optional[str] = None,
        return_response: bool = True,
        log_level: Any = None,
        include_trace: bool = False,
        custom_error_map: Optional[Dict[type, str]] = None,
    ) -> Callable:
        """Decorator for automatic error handling.

        Args:
            operation_name: Operation name (inferred from function if None)
            component: Component name (inferred from module if None)
            return_response: Return UnifiedResponseService.error() or re-raise
            log_level: Logging level for errors
            include_trace: Include stack trace in response
            custom_error_map: Custom exception to message mapping

        Returns:
            Decorator function
        """
        ...


class HTTPErrorHandlerProtocol(Protocol):
    """Protocol for HTTP-specific error handling."""

    def __call__(
        self,
        default_status: int = 500,
        error_mappings: Optional[Dict[type, int]] = None,
    ) -> Callable:
        """Decorator for HTTP endpoint error handling.

        Args:
            default_status: Default status code for unmapped errors
            error_mappings: Exception to HTTP status code mapping

        Returns:
            Decorator function
        """
        ...


class ServiceErrorHandlerProtocol(Protocol):
    """Protocol for service-level error handling."""

    def __call__(self, service_name: str) -> Callable:
        """Decorator for service method error handling.

        Args:
            service_name: Service name for logging/tracking

        Returns:
            Decorator function
        """
        ...


class RepositoryErrorHandlerProtocol(Protocol):
    """Protocol for repository-level error handling."""

    def __call__(self, entity_name: str = "entity") -> Callable:
        """Decorator for repository method error handling.

        Args:
            entity_name: Entity name for error messages

        Returns:
            Decorator function
        """
        ...


class InfrastructureErrorHandlerProtocol(Protocol):
    """Protocol for infrastructure-level error handling."""

    def __call__(self, component_name: str = "infrastructure") -> Callable:
        """Decorator for infrastructure component error handling.

        Args:
            component_name: Infrastructure component name

        Returns:
            Decorator function
        """
        ...
