# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
NFC Routes Bootstrap

Bootstrap/factory class for NFC integration routes.
Single Responsibility: Initialize and register NFC API routes with dependencies.
"""

from fastapi import FastAPI
from socketio import AsyncServer

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.api.endpoints.nfc_api_routes import NFCAPIRoutes
from app.src.infrastructure.error_handling.unified_error_handler import (
    unified_error_handler,
    service_unavailable_error,
)

logger = get_logger(__name__)


class UnifiedNFCRoutes:
    """
    Bootstrap class for NFC API routes.

    Responsibilities:
    - Initialize NFCAPIRoutes with dependencies
    - Register routes with FastAPI app
    - Configure Socket.IO for NFC service
    - Provide dependency injection for NFC service and state manager

    Does NOT handle:
    - HTTP request processing (delegated to NFCAPIRoutes)
    - NFC hardware operations (delegated to NFC service)
    - State broadcasting (delegated to state manager)
    """

    def __init__(self, app: FastAPI, socketio: AsyncServer):
        """Initialize NFC routes bootstrap.

        Args:
            app: FastAPI application instance
            socketio: Socket.IO server for real-time events
        """
        self.app = app
        self.socketio = socketio
        self.error_handler = unified_error_handler
        self.api_routes = None

        # Configure Socket.IO for NFC service if available
        self._configure_nfc_socketio()

    def _configure_nfc_socketio(self):
        """Configure Socket.IO for the NFC service."""
        application = getattr(self.app, "application", None)
        if application:
            # Try new NFC application service first
            nfc_service = getattr(application, "_nfc_app_service", None)
            if not nfc_service or not hasattr(nfc_service, "set_socketio"):
                # Fallback to legacy NFC service
                nfc_service = getattr(application, "_nfc_app_service", None)
            if nfc_service and hasattr(nfc_service, "set_socketio"):
                nfc_service.set_socketio(self.socketio)
                logger.info("✅ Socket.IO configured for NFC service")
            else:
                logger.info("ℹ️ NFC service doesn't support Socket.IO (using direct callbacks)")
        else:
            logger.warning("⚠️ Domain application not available for Socket.IO configuration")

    @handle_errors("nfc_routes_init", return_response=False)
    def initialize(self):
        """Initialize NFC API routes with dependency injection."""
        # Create NFC service getter function
        def get_nfc_service(request):
            """Get NFC service from domain application."""
            application = getattr(request.app, "application", None)
            if not application:
                raise service_unavailable_error("Domain application not available")
            nfc_service = getattr(application, "_nfc_app_service", None)
            if not nfc_service:
                raise service_unavailable_error("NFC service not available")
            return nfc_service

        # Create state manager getter function
        def get_state_manager(request):
            """Get state manager from application."""
            return getattr(request.app, "state_manager", None)

        # Initialize API routes
        self.api_routes = NFCAPIRoutes(
            nfc_service_getter=get_nfc_service,
            state_manager_getter=get_state_manager
        )
        logger.info("✅ NFC API routes initialized")

    def register_with_app(self, prefix: str = "/api/nfc"):
        """Register the router with the FastAPI app.

        Args:
            prefix: URL prefix for NFC routes (default: /api/nfc)
        """
        if not self.api_routes:
            self.initialize()

        self.app.include_router(self.api_routes.get_router(), prefix=prefix, tags=["nfc"])
        logger.info(f"✅ Unified NFC routes registered with prefix: {prefix}")
