# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Upload Routes Bootstrap

Bootstrap/factory class for upload session management routes.
Single Responsibility: Initialize and register upload API routes with dependencies.
"""

from fastapi import FastAPI
from socketio import AsyncServer

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.api.endpoints.upload_api_routes import UploadAPIRoutes

logger = get_logger(__name__)


class UploadRoutes:
    """
    Bootstrap class for upload management routes.

    Responsibilities:
    - Initialize UploadAPIRoutes with dependencies
    - Register routes with FastAPI app
    - Provide dependency injection for upload controller

    Does NOT handle:
    - HTTP request processing (delegated to UploadAPIRoutes)
    - Upload session logic (delegated to upload controller)
    """

    def __init__(self, app: FastAPI, socketio: AsyncServer):
        """Initialize upload routes bootstrap.

        Args:
            app: FastAPI application instance
            socketio: Socket.IO server for real-time events
        """
        self.app = app
        self.socketio = socketio
        self.api_routes = None

    @handle_errors("upload_routes_init", return_response=False)
    def initialize(self):
        """Initialize upload API routes with dependency injection."""
        # Create upload controller getter function
        def get_upload_controller(request):
            """Get upload controller from app state."""
            playlist_routes_ddd = getattr(request.app, "playlist_routes_ddd", None)
            if playlist_routes_ddd and hasattr(playlist_routes_ddd, "upload_controller"):
                return playlist_routes_ddd.upload_controller
            return None

        # Initialize API routes
        self.api_routes = UploadAPIRoutes(upload_controller_getter=get_upload_controller)
        logger.info("✅ Upload API routes initialized")

    def register_with_app(self, prefix: str = "/api/uploads"):
        """Register the router with the FastAPI app.

        Args:
            prefix: URL prefix for upload routes (default: /api/uploads)
        """
        if not self.api_routes:
            self.initialize()

        self.app.include_router(self.api_routes.get_router(), prefix=prefix, tags=["uploads"])
        logger.info(f"✅ Upload routes registered with prefix: {prefix}")
