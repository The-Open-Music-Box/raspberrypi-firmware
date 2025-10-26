# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Response utilities for consistent API responses.

This module provides centralized utilities for creating consistent API responses
with proper headers, error handling, and JSON formatting.
"""

from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


class ResponseUtils:
    """Utility class for creating consistent API responses."""

    @staticmethod
    def create_json_response(
        data: Dict[str, Any], status_code: int = 200, add_anti_cache_headers: bool = True
    ) -> JSONResponse:
        """Create a standardized JSON response.

        Args:
            data: Response data dictionary
            status_code: HTTP status code
            add_anti_cache_headers: Whether to add anti-cache headers

        Returns:
            JSONResponse with standardized format and headers
        """
        response = JSONResponse(content=data, status_code=status_code)

        if add_anti_cache_headers:
            ResponseUtils._add_anti_cache_headers(response)

        return response

    @staticmethod
    def create_success_response(
        message: str, data: Optional[Dict[str, Any]] = None, status_code: int = 200
    ) -> JSONResponse:
        """Create a standardized success response.

        Args:
            message: Success message
            data: Optional additional data
            status_code: HTTP status code

        Returns:
            JSONResponse with success format
        """
        response_data = {"status": "success", "message": message}

        if data:
            response_data.update(data)

        return ResponseUtils.create_json_response(response_data, status_code)

    @staticmethod
    def create_error_response(
        error_message: str, status_code: int = 500, error_details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """Create a standardized error response.

        Args:
            error_message: Error message
            status_code: HTTP status code
            error_details: Optional additional error details

        Returns:
            JSONResponse with error format
        """
        response_data = {"status": "error", "message": error_message}

        if error_details:
            response_data["details"] = error_details

        return ResponseUtils.create_json_response(response_data, status_code)

    @staticmethod
    def _add_anti_cache_headers(response: JSONResponse) -> None:
        """Add anti-cache headers to a response.

        Args:
            response: JSONResponse to add headers to
        """
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
