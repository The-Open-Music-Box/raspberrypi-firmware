# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
FastAPI Application Entry Point for TheOpenMusicBox

This module provides the main FastAPI application with Socket.IO integration
for the TheOpenMusicBox music management system. It handles application
lifecycle, domain bootstrap initialization, and proper resource cleanup.

Key Components:
- FastAPI application with CORS middleware
- Socket.IO server for real-time communication
- Domain-driven architecture initialization
- Physical controls integration
- Graceful startup and shutdown procedures
"""

from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.src.config import config
from app.src.core.application import Application
from app.src.monitoring import get_logger
from app.src.monitoring.logging.log_level import LogLevel
from app.src.routes.factories.api_routes_state import init_api_routes_state
from app.src.infrastructure.error_handling.unified_error_handler import (
    UnifiedErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
)
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)
error_handler = UnifiedErrorHandler()

env_config = config

# Parse CORS origins
if isinstance(env_config.cors_allowed_origins, str):
    cors_origins = [
        origin.strip() for origin in env_config.cors_allowed_origins.split(";") if origin.strip()
    ]
else:
    cors_origins = env_config.cors_allowed_origins

# Initialize Socket.IO server with unified configuration
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*" if "*" in cors_origins else cors_origins,
    ping_timeout=20,
    ping_interval=10,
    logger=False,
    engineio_logger=False
)

@handle_errors(operation_name="initialize_application", component="main.startup")
async def _initialize_application(fastapi_app):
    """Initialize the application instance."""
    # Attach DI container to FastAPI app for route access
    from app.src.infrastructure.di.container import get_container
    container = get_container()
    fastapi_app.container = container
    logger.log(LogLevel.INFO, "✅ DI container attached to FastAPI app")

    # Get audio backend from container if available (avoids circular import)
    audio_backend = None
    try:
        if container.has("audio_backend"):
            audio_backend = container.get("audio_backend")
            logger.log(LogLevel.INFO, f"🎵 Retrieved audio backend from DI: {type(audio_backend).__name__}")
    except Exception as e:
        logger.log(LogLevel.DEBUG, f"Audio backend not yet in container: {e}")

    # Initialize the application with injected audio backend (this registers all DI services including database)
    app_instance = Application(env_config, audio_backend=audio_backend)
    fastapi_app.application = await app_instance.initialize_async()

    # Now verify database health after services are registered
    from app.src.dependencies import get_database_manager
    logger.log(LogLevel.INFO, "🔧 Verifying database health...")
    try:
        db_manager = get_database_manager()
        health_info = db_manager.get_health_info()
        if health_info["status"] == "healthy":
            logger.log(LogLevel.INFO, f"✅ Database ready with {health_info['tables_count']} tables")
        else:
            logger.log(LogLevel.ERROR, f"❌ Database health check failed: {health_info}")
            raise RuntimeError(f"Database initialization failed: {health_info.get('error', 'Unknown error')}")
    except Exception as e:
        logger.log(LogLevel.ERROR, f"❌ Critical database health check error: {e}")
        raise

    return app_instance


@handle_errors(operation_name="start_domain_bootstrap", component="main.startup")
async def _start_domain_bootstrap():
    """Start the domain bootstrap.

    This initializes all domain services including:
    - Physical controls (GPIO/mock)
    - Audio backends
    - State management
    - Event bus
    """
    from app.src.infrastructure.di.container import get_container
    container = get_container()
    domain_bootstrap = container.get("domain_bootstrap")

    if domain_bootstrap.is_initialized:
        await domain_bootstrap.start()
        logger.log(LogLevel.INFO, "✅ Domain bootstrap started (includes physical controls)")
    else:
        context = ErrorContext(
            component="main.startup",
            operation="start_domain_bootstrap",
            category=ErrorCategory.GENERAL,
            severity=ErrorSeverity.MEDIUM,
        )
        error_handler.handle_error(RuntimeError("Domain bootstrap not initialized"), context)


@handle_errors(operation_name="cleanup_playlist_routes", component="main.shutdown")
async def _cleanup_playlist_routes(playlist_routes):
    """Cleanup playlist routes resources."""
    if not playlist_routes:
        return

    # Stop background tasks first
    if hasattr(playlist_routes, "cleanup_background_tasks"):
        await playlist_routes.cleanup_background_tasks()
        logger.log(LogLevel.INFO, "main.py: Background tasks cleaned up successfully.")

    # Then cleanup physical controls
    if hasattr(playlist_routes, "cleanup_controls"):
        await playlist_routes.cleanup_controls()
        logger.log(LogLevel.INFO, "main.py: Physical controls cleaned up successfully.")


@handle_errors(operation_name="cleanup_application", component="main.shutdown")
async def _cleanup_application(fastapi_app):
    """Cleanup application instance."""
    app_instance = getattr(fastapi_app, "application", None)
    if app_instance and hasattr(app_instance, "cleanup"):
        await app_instance.cleanup()
        logger.info("✅ Application instance cleaned up")


@handle_errors(operation_name="cleanup_domain", component="main.shutdown")
async def _cleanup_domain():
    """Cleanup domain architecture.

    This stops and cleans up all domain services including:
    - Physical controls
    - Audio backends
    - State management
    - Background tasks
    """
    from app.src.infrastructure.di.container import get_container
    container = get_container()
    domain_bootstrap = container.get("domain_bootstrap")

    if domain_bootstrap.is_initialized:
        await domain_bootstrap.stop()
        domain_bootstrap.cleanup()
        logger.log(LogLevel.INFO, "✅ Domain architecture cleaned up")


@handle_errors(operation_name="cleanup_socketio", component="main.shutdown")
async def _cleanup_socketio():
    """Cleanup Socket.IO server to release port binding."""
    try:
        # Disconnect all clients
        for sid in list(sio.manager.rooms.get("/", {}).keys()):
            await sio.disconnect(sid)
        logger.log(LogLevel.INFO, "✅ Socket.IO clients disconnected")

        # Shutdown the Socket.IO server
        await sio.shutdown()
        logger.log(LogLevel.INFO, "✅ Socket.IO server shut down")
    except Exception as e:
        logger.log(LogLevel.WARNING, f"⚠️ Error during Socket.IO cleanup: {e}")


@asynccontextmanager
async def lifespan(fastapi_app):
    """Application lifespan event handler for FastAPI startup and shutdown.

    Startup sequence:
    1. Initialize database
    2. Start domain bootstrap (physical controls, audio, state)
    3. Initialize API routes

    Shutdown sequence:
    1. Cleanup playlist routes (background tasks)
    2. Cleanup application
    3. Cleanup domain (stops physical controls, audio, state)
    4. Cleanup Socket.IO

    Args:
        fastapi_app: The FastAPI application instance.

    Yields:
        None: Control during application runtime.
    """
    routes_organizer = None
    try:
        # Startup sequence
        await _initialize_application(fastapi_app)
        await _start_domain_bootstrap()

        routes_organizer = init_api_routes_state(fastapi_app, sio, env_config)

        logger.log(LogLevel.INFO, "🟢 Application startup completed successfully")
        yield
        logger.log(LogLevel.INFO, "🟡 Application shutdown sequence starting...")

    except Exception as e:
        context = ErrorContext(
            component="main.lifespan",
            operation="startup",
            category=ErrorCategory.GENERAL,
            severity=ErrorSeverity.CRITICAL,
        )
        error_handler.handle_error(e, context)
        raise

    finally:
        # Shutdown sequence (reverse order of startup)
        playlist_routes = (
            getattr(routes_organizer, "playlist_routes", None) if routes_organizer else None
        )
        await _cleanup_playlist_routes(playlist_routes)
        await _cleanup_application(fastapi_app)
        await _cleanup_domain()
        await _cleanup_socketio()

        logger.log(LogLevel.INFO, "✅ Application shutdown completed")


from app.src.config.openapi_config import get_openapi_config, customize_openapi_schema

# Create FastAPI app with enhanced OpenAPI configuration
openapi_config = get_openapi_config()
_fastapi_app = FastAPI(
    lifespan=lifespan,
    **openapi_config
)

# Add CORS middleware
_fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Customize OpenAPI schema with additional information
# Save reference to original openapi method before overriding
_original_openapi = _fastapi_app.openapi

def custom_openapi():
    """Generate customized OpenAPI schema."""
    if _fastapi_app.openapi_schema:
        return _fastapi_app.openapi_schema

    # Call the ORIGINAL openapi method (not the overridden one)
    openapi_schema = _original_openapi()
    customized_schema = customize_openapi_schema(openapi_schema)
    _fastapi_app.openapi_schema = customized_schema
    return _fastapi_app.openapi_schema

_fastapi_app.openapi = custom_openapi

# Wrap FastAPI app with Socket.IO and export as 'app_sio' for uvicorn
app_sio = socketio.ASGIApp(sio, other_asgi_app=_fastapi_app)

# Also export as 'app' for backward compatibility and local development
app = app_sio
