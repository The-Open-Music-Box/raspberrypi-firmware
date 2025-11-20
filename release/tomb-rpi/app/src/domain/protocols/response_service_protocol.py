# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Response Service Protocol.

Defines the interface for response formatting services.
Framework-agnostic protocol - implementations can use any HTTP framework.
"""

from typing import Protocol, Dict, Any, Optional, List


class ResponseServiceProtocol(Protocol):
    """Protocol for response formatting services.

    Framework-agnostic protocol. Implementations return framework-specific
    response objects (e.g., FastAPI's JSONResponse), but the protocol uses
    generic 'Any' type to maintain domain purity.
    """

    @staticmethod
    def success(
        message: str,
        data: Optional[Any] = None,
        status_code: int = 200,
        server_seq: Optional[int] = None,
        client_op_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Create a standardized success response.

        Args:
            message: Success message
            data: Data to return
            status_code: HTTP status code (default: 200)
            server_seq: Sequence number for synchronization
            client_op_id: Client operation ID for tracking
            metadata: Additional metadata

        Returns:
            Framework-specific response object with unified format
        """
        ...

    @staticmethod
    def error(
        message: str,
        error_type: str = "error",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
        trace: bool = False,
    ) -> Any:
        """Create a standardized error response.

        Args:
            message: Error message
            error_type: Type of error
            status_code: HTTP status code
            details: Additional error details
            client_op_id: Client operation ID for tracking
            trace: Include stack trace

        Returns:
            Framework-specific response object with error information
        """
        ...

    @staticmethod
    def validation_error(
        errors: List[Dict[str, Any]],
        message: str = "Validation failed",
        client_op_id: Optional[str] = None,
    ) -> Any:
        """Create a validation error response.

        Args:
            errors: List of validation errors
            message: Error message
            client_op_id: Client operation ID

        Returns:
            Framework-specific response object with validation errors
        """
        ...

    @staticmethod
    def not_found(
        resource: str,
        resource_id: Optional[str] = None,
        client_op_id: Optional[str] = None,
    ) -> Any:
        """Create a not found error response.

        Args:
            resource: Resource type
            resource_id: Resource identifier
            client_op_id: Client operation ID

        Returns:
            Framework-specific response object with 404 status
        """
        ...

    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        operation: Optional[str] = None,
        client_op_id: Optional[str] = None,
        trace: bool = False,
    ) -> Any:
        """Create an internal error response.

        Args:
            message: Error message
            operation: Operation that failed
            client_op_id: Client operation ID
            trace: Include stack trace

        Returns:
            Framework-specific response object with 500 status
        """
        ...

    @staticmethod
    def bad_request(
        message: str,
        details: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
    ) -> Any:
        """Create a bad request error response.

        Args:
            message: Error message
            details: Additional details
            client_op_id: Client operation ID

        Returns:
            Framework-specific response object with 400 status
        """
        ...
