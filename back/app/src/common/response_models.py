# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Standardized response models for TheOpenMusicBox API.

This module defines consistent response formats, error handling, and data contracts
that are used throughout the entire backend API to ensure frontend compatibility.
"""

import time
import uuid
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseStatus(str, Enum):
    """Standard response status values."""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class ErrorType(str, Enum):
    """Standard error types for consistent error handling."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"
    CONFLICT = "conflict"
    BAD_REQUEST = "bad_request"


class BaseResponse(BaseModel, Generic[T]):
    """Base response model that all API responses must follow."""

    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Human-readable message")
    data: T | None = Field(None, description="Response data payload")
    timestamp: float = Field(
        default_factory=time.time,
        description="Response timestamp in seconds",
    )
    server_seq: int | None = Field(
        None, description="Server sequence number for state synchronization"
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""

    status: ResponseStatus = Field(
        ResponseStatus.ERROR, description="Always 'error' for error responses"
    )
    message: str = Field(..., description="Human-readable error message")
    error_type: ErrorType = Field(..., description="Structured error type")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: float = Field(
        default_factory=time.time,
        description="Error timestamp in seconds",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Request identifier for debugging",
    )


class SuccessResponse(BaseResponse[T]):
    """Standard success response format."""

    status: ResponseStatus = Field(
        ResponseStatus.SUCCESS, description="Always 'success' for success responses"
    )


class PaginatedData(BaseModel, Generic[T]):
    """Standard pagination wrapper for list responses."""

    items: list[T] = Field(..., description="List of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class PaginatedResponse(BaseResponse[PaginatedData[T]]):
    """Standard paginated response format."""

    status: ResponseStatus = Field(ResponseStatus.SUCCESS)


# Common request models
class ClientOperationRequest(BaseModel):
    """Base model for requests that include client operation tracking."""

    client_op_id: str | None = Field(
        default=None,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]*$",
        description="Client operation identifier for request tracking",
    )


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")


# Response utility functions
def create_success_response(
    message: str, data: Any | None = None, server_seq: int | None = None
) -> dict[str, Any]:
    """Create a standardized success response."""
    return SuccessResponse[Any](
        status=ResponseStatus.SUCCESS, message=message, data=data, server_seq=server_seq
    ).model_dump(exclude_none=True)


def create_error_response(
    message: str, error_type: ErrorType, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create a standardized error response."""
    return ErrorResponse(
        status=ResponseStatus.ERROR, message=message, error_type=error_type, details=details
    ).model_dump(exclude_none=True)


def create_paginated_response(
    message: str,
    items: list[Any],
    page: int,
    limit: int,
    total: int,
    server_seq: int | None = None,
) -> dict[str, Any]:
    """Create a standardized paginated response."""
    total_pages = (total + limit - 1) // limit  # Ceiling division

    paginated_data = PaginatedData[Any](
        items=items, page=page, limit=limit, total=total, total_pages=total_pages
    )

    return PaginatedResponse[Any](
        status=ResponseStatus.SUCCESS, message=message, data=paginated_data, server_seq=server_seq
    ).model_dump(exclude_none=True)


# HTTP status code mapping for error types
ERROR_STATUS_CODES = {
    ErrorType.VALIDATION_ERROR: 400,
    ErrorType.BAD_REQUEST: 400,
    ErrorType.NOT_FOUND: 404,
    ErrorType.PERMISSION_DENIED: 403,
    ErrorType.RATE_LIMIT_EXCEEDED: 429,
    ErrorType.SERVICE_UNAVAILABLE: 503,
    ErrorType.INTERNAL_ERROR: 500,
    ErrorType.CONFLICT: 409,
}


def get_http_status_for_error(error_type: ErrorType) -> int:
    """Get appropriate HTTP status code for error type."""
    return ERROR_STATUS_CODES.get(error_type, 500)


# Simple Result Pattern for Service Layer
class Result(Generic[T]):
    """Simple result pattern for service layer operations."""

    def __init__(self, success: bool, data: T | None = None, error: str | None = None):
        self.success = success
        self.data = data
        self.error = error

    @classmethod
    def success_result(cls, data: T | None = None) -> "Result[T]":
        """Create a successful result."""
        return cls(success=True, data=data)

    @classmethod
    def error_result(cls, error: str) -> "Result[T]":
        """Create an error result."""
        return cls(success=False, error=error)


def Success(data: T | None = None) -> Result[T]:
    """Create a successful result (convenience function)."""
    return Result.success_result(data)


def Error(error: str) -> Result[Any]:
    """Create an error result (convenience function)."""
    return Result.error_result(error)
