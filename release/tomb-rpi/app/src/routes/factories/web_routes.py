# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Web Routes Bootstrap

Bootstrap/factory class for web static file serving and SPA routing.
Single Responsibility: Initialize and register web API routes with dependencies.
"""

from pathlib import Path
from fastapi import FastAPI

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.api.endpoints.web_api_routes import WebAPIRoutes

logger = get_logger(__name__)


class WebRoutes:
    """
    Bootstrap class for web (static file) routes.

    Responsibilities:
    - Initialize WebAPIRoutes with static directory path
    - Register routes directly with FastAPI app (web routes use direct mounting)
    - Configure SPA routing

    Does NOT handle:
    - Actual file serving (delegated to WebAPIRoutes)
    - SPA routing logic (delegated to WebAPIRoutes)
    - Static file caching (delegated to FastAPI's StaticFiles)
    """

    def __init__(self, app: FastAPI):
        """Initialize web routes bootstrap.

        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.api_routes = None
        self.static_dir = Path("app/static")

    @handle_errors("web_routes_init", return_response=False)
    def initialize(self):
        """Initialize web API routes with static directory."""
        # Initialize API routes with static directory path
        self.api_routes = WebAPIRoutes(static_dir=self.static_dir)
        logger.info("✅ Web API routes initialized")

    def register(self):
        """Register web routes with the FastAPI application."""
        if not self.api_routes:
            self.initialize()

        # Register routes directly with app (web routes use direct mounting, not router)
        self.api_routes.register_with_app(self.app)
        logger.info("✅ Web routes registered successfully")
