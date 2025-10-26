# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
System Routes Bootstrap

Bootstrap/factory class for system-level routes.
Single Responsibility: Initialize and register system API routes with dependencies.
"""

from fastapi import FastAPI

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.api.endpoints.system_api_routes import SystemAPIRoutes

logger = get_logger(__name__)


class SystemRoutes:
    """
    Bootstrap class for system-level API routes.

    Responsibilities:
    - Initialize SystemAPIRoutes with dependencies
    - Register routes with FastAPI app
    - Provide dependency injection for playback coordinator

    Does NOT handle:
    - HTTP request processing (delegated to SystemAPIRoutes)
    - System operations (delegated to system services)
    - Health monitoring (delegated to monitoring services)
    """

    def __init__(self, app: FastAPI):
        """Initialize system routes bootstrap.

        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.api_routes = None

    @handle_errors("system_routes_init", return_response=False)
    def initialize(self):
        """Initialize system API routes with dependency injection."""
        # Create playback coordinator getter function
        def get_playback_coordinator(request):
            """Get playback coordinator from DI container."""
            from app.src.dependencies import get_playback_coordinator as get_coord
            try:
                return get_coord()
            except Exception as e:
                logger.error(f"Failed to get playback coordinator: {e}")
                return None

        # Initialize API routes
        self.api_routes = SystemAPIRoutes(
            playback_coordinator_getter=get_playback_coordinator
        )
        logger.info("✅ System API routes initialized")

    def register(self):
        """Register system routes with the FastAPI application."""
        if not self.api_routes:
            self.initialize()

        # Register the router
        self.app.include_router(self.api_routes.get_router())
        logger.info("✅ System API routes registered")
