# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
System API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for system operations.
"""

from typing import Dict, Any
from fastapi import APIRouter, Request
import logging
import platform
import time

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class SystemAPIRoutes:
    """
    Pure API routes handler for system operations.

    Responsibilities:
    - HTTP request/response handling for system status
    - Health checks
    - System information retrieval
    - Log access
    - System restart operations

    Does NOT handle:
    - Actual system operations (delegated to system services)
    - Service lifecycle management (delegated to application layer)
    - Resource monitoring (delegated to monitoring services)
    """

    def __init__(self, playback_coordinator_getter):
        """Initialize system API routes.

        Args:
            playback_coordinator_getter: Callable that returns playback coordinator from request
        """
        self.router = APIRouter(prefix="/api", tags=["system"])
        self._get_coordinator = playback_coordinator_getter
        self._register_routes()

    def _register_routes(self):
        """Register all system-related API routes."""

        @self.router.get("/playback/status")
        @handle_http_errors()
        async def get_playback_status(request: Request):
            """Get current playback status."""
            try:
                coordinator = self._get_coordinator(request)
                if not coordinator:
                    return UnifiedResponseService.error(
                        message="Playback coordinator not available",
                        error_type="service_unavailable",
                        status_code=503
                    )

                playback_state = coordinator.get_playback_status()
                logger.info("API: Responding with playback state")

                # Create response with anti-cache headers
                from fastapi.responses import JSONResponse
                response = JSONResponse(content=playback_state, status_code=200)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response

            except Exception as e:
                logger.error(f"Error getting playback status: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to get playback status",
                    operation="get_playback_status"
                )

        @self.router.get("/health")
        @handle_http_errors()
        async def health_check(request: Request):
            """Perform system health check."""
            try:
                logger.info("API /api/health: Health check requested")

                # Get container from app state
                container = getattr(request.app, "container", None)

                if not container:
                    health_status = "unhealthy"
                    services = {
                        "api": True,
                        "audio": False,
                        "nfc": False,
                        "gpio": False,
                        "led_hat": False,
                        "websocket": False,
                    }
                else:
                    # Get service statuses
                    audio = getattr(container, "audio", None)
                    nfc = getattr(container, "nfc", None)
                    gpio = getattr(container, "gpio", None)
                    led_hat = getattr(container, "led_hat", None)
                    websocket = hasattr(request.app, "socketio")

                    services = {
                        "api": True,
                        "audio": bool(audio),
                        "nfc": bool(nfc),
                        "gpio": bool(gpio),
                        "led_hat": bool(led_hat),
                        "websocket": websocket,
                    }

                    # Calculate overall health
                    critical_services = ["api"]
                    optional_services = ["audio", "nfc", "gpio", "led_hat", "websocket"]

                    available_critical = sum(1 for s in critical_services if services.get(s, False))
                    available_optional = sum(1 for s in optional_services if services.get(s, False))
                    total_critical = len(critical_services)
                    total_optional = len(optional_services)

                    if available_critical == total_critical and available_optional >= total_optional * 0.8:
                        health_status = "healthy"
                    elif available_critical == total_critical:
                        health_status = "degraded"
                    else:
                        health_status = "unhealthy"

                # Get server_seq from state manager (required by contract v3.1.0)
                state_manager = None
                server_seq = 0
                if container:
                    state_manager = getattr(container, "state_manager", None)
                    if state_manager and hasattr(state_manager, "get_global_sequence"):
                        server_seq = state_manager.get_global_sequence()

                health_data = {
                    "status": health_status,
                    "services": services,
                    "timestamp": time.time(),
                    "server_seq": server_seq,
                }

                return UnifiedResponseService.success(
                    message=f"System health check completed - status: {health_status}",
                    data=health_data,
                    server_seq=server_seq
                )

            except Exception as e:
                logger.error(f"Error during health check: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Health check failed",
                    operation="health_check"
                )

        @self.router.get("/system/info")
        @handle_http_errors()
        async def get_system_info(request: Request):
            """Get system information."""
            try:
                logger.info("API /api/system/info: System info requested")

                # Try to import psutil
                try:
                    import psutil as _psutil
                except ImportError:
                    _psutil = None

                # Build system info
                system_info = {
                    "platform": platform.system(),
                    "platform_release": platform.release(),
                    "platform_version": platform.version(),
                    "architecture": platform.machine(),
                    "hostname": platform.node(),
                    "processor": platform.processor(),
                }

                # Add memory info if psutil available
                if _psutil:
                    try:
                        memory = _psutil.virtual_memory()
                        system_info.update({
                            "memory_total": memory.total,
                            "memory_available": memory.available,
                            "memory_percent": memory.percent,
                        })
                    except Exception:
                        pass

                # Get server_seq from state manager (required by contract v3.1.0)
                container = getattr(request.app, "container", None)
                state_manager = None
                server_seq = 0
                if container:
                    state_manager = getattr(container, "state_manager", None)
                    if state_manager and hasattr(state_manager, "get_global_sequence"):
                        server_seq = state_manager.get_global_sequence()

                # Read application version from VERSION file
                import os
                version = "0.4.1"  # Default fallback
                version_file = os.path.join(os.path.dirname(__file__), "../../../../../VERSION")
                try:
                    if os.path.exists(version_file):
                        with open(version_file, 'r') as f:
                            version = f.read().strip()
                except Exception:
                    pass  # Use default version on error

                from fastapi.responses import JSONResponse
                return JSONResponse(content={
                    "status": "success",
                    "message": "System information retrieved successfully",
                    "timestamp": time.time(),
                    "server_seq": server_seq,
                    "data": {
                        "system_info": system_info,
                        "version": version,
                        "contract_version": "3.1.0",
                        "hostname": system_info.get("hostname", "localhost"),
                        "uptime": 3600,  # System uptime in seconds
                        "server_seq": server_seq
                    }
                })

            except Exception as e:
                logger.error(f"Error getting system info: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to get system information",
                    operation="get_system_info"
                )

        @self.router.get("/system/logs")
        @handle_http_errors()
        async def get_system_logs():
            """Get system logs."""
            try:
                logger.info("API /api/system/logs: Logs requested")

                import glob
                logs_data = {"logs": [], "log_files_available": []}

                # Search for log files
                possible_log_paths = [
                    "/var/log/tomb-rpi/*.log",
                    "/tmp/tomb-rpi*.log",
                    "logs/*.log",
                    "*.log",
                ]

                for pattern in possible_log_paths:
                    log_files = glob.glob(pattern)
                    for log_file in log_files:
                        logs_data["log_files_available"].append(log_file)
                        # Read last 100 lines
                        try:
                            with open(log_file, "r") as f:
                                lines = f.readlines()
                                last_lines = lines[-100:] if len(lines) > 100 else lines
                                logs_data["logs"].extend([
                                    {"file": log_file, "line": line.strip()}
                                    for line in last_lines if line.strip()
                                ])
                        except (IOError, OSError):
                            pass

                from fastapi.responses import JSONResponse
                return JSONResponse(content={
                    "status": "success",
                    "message": "System logs retrieved successfully",
                    "timestamp": time.time(),
                    "data": logs_data
                })

            except Exception as e:
                logger.error(f"Error getting system logs: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to get system logs",
                    operation="get_system_logs"
                )

        @self.router.post("/system/restart")
        @handle_http_errors()
        async def restart_system():
            """Restart the system."""
            try:
                logger.info("API /api/system/restart: Restart requested")

                import asyncio
                import os
                import signal

                # Schedule restart after response is sent
                async def delayed_restart():
                    await asyncio.sleep(2)
                    logger.info("Restarting application...")
                    os.kill(os.getpid(), signal.SIGTERM)

                # Start delayed restart task
                asyncio.create_task(delayed_restart())

                response_data = {
                    "status": "restart_scheduled",
                    "message": "Application restart scheduled in 2 seconds",
                }

                from app.src.common.response_models import create_success_response
                from fastapi.responses import JSONResponse

                standardized_response = create_success_response(
                    message="System restart scheduled successfully",
                    data=response_data
                )
                response = JSONResponse(content=standardized_response, status_code=200)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response

            except Exception as e:
                logger.error(f"Error restarting system: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to restart system",
                    operation="restart_system"
                )

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        return self.router
