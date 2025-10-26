# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Web API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for static files and SPA routing.
"""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)


class WebAPIRoutes:
    """
    Pure API routes handler for web static file serving.

    Responsibilities:
    - Serving static files (CSS, JS, images)
    - Handling SPA routing fallback to index.html
    - Managing root path requests
    - Error handling for missing files

    Does NOT handle:
    - API endpoint routing (delegated to other route handlers)
    - Application logic (delegated to services)
    - Authentication/authorization (delegated to middleware)
    """

    def __init__(self, static_dir: Path):
        """Initialize web API routes.

        Args:
            static_dir: Path to static files directory
        """
        self.static_dir = static_dir
        self.router = None  # Web routes use direct app mounting

        # Validate static directory exists
        if not self.static_dir.exists() or not self.static_dir.is_dir():
            logger.warning(f"Static directory not found: {self.static_dir}")

    def register_with_app(self, app):
        """Register web routes directly with FastAPI app.

        Note: Web routes are registered directly on the app rather than
        using an APIRouter, because they need to handle catch-all paths
        and static file mounting.

        Args:
            app: FastAPI application instance
        """
        try:
            if not self.static_dir.exists() or not self.static_dir.is_dir():
                logger.warning(f"Static directory {self.static_dir} not found")
                return

            # Mount static files
            from fastapi.staticfiles import StaticFiles
            app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
            logger.info(f"Mounted static files from {self.static_dir}")

            # Root path handler - serve index.html
            @app.get("/")
            async def serve_spa_index():
                """Serve SPA index.html for root path."""
                index_path = self.static_dir / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path))
                else:
                    logger.error("index.html not found in static directory")
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404, detail="Frontend not available")

            # Catch-all route for SPA client-side routing
            @app.get("/{full_path:path}", include_in_schema=False)
            async def serve_spa(full_path: str):
                """
                Handle SPA client-side routing.

                - If path starts with 'api/', let API routers handle it
                - If file exists in static dir, serve it
                - Otherwise, return index.html for SPA routing
                """
                # Don't intercept API or Socket.IO routes
                if full_path.startswith("api/") or full_path.startswith("socket.io"):
                    return None  # Let FastAPI/Socket.IO continue looking for matching routes

                # Check if requested file exists
                requested_file = self.static_dir / full_path
                if requested_file.exists() and requested_file.is_file():
                    return FileResponse(str(requested_file))

                # Return index.html for SPA routing
                index_path = self.static_dir / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path))
                else:
                    logger.error("index.html not found in static directory")
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404, detail="Frontend not available")

            logger.info("SPA routing configured successfully")

        except Exception as e:
            logger.error(f"Error registering web routes: {e}", exc_info=True)
            raise

    def get_router(self) -> APIRouter:
        """
        Web routes don't use a router pattern.

        Returns None since web routes are registered directly on the app.
        """
        return None
