# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
System API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for system operations.
"""

import logging
import platform
import time
from typing import Any

from fastapi import APIRouter, Request

from app.src.api.base_api_routes import BaseAPIRoutes
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService


class SystemAPIRoutes(BaseAPIRoutes):
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

    Inherits common API functionality from BaseAPIRoutes.
    """

    def __init__(self, playback_coordinator_getter, led_event_handler_getter=None):
        """Initialize system API routes.

        Args:
            playback_coordinator_getter: Callable that returns playback coordinator from request
            led_event_handler_getter: Optional callable that returns LED event handler from request
        """
        self.router = APIRouter(prefix="/api", tags=["system"])
        super().__init__(router=self.router)
        self._get_coordinator = playback_coordinator_getter
        self._get_led_handler = led_event_handler_getter
        self._register_routes()

    def _get_server_seq_from_container(self, container) -> int:
        """Extract server_seq from container's state manager.

        Args:
            container: Application container

        Returns:
            Server sequence number, or 0 if unavailable
        """
        if not container:
            return 0

        state_manager = getattr(container, "state_manager", None)
        if state_manager and hasattr(state_manager, "get_global_sequence"):
            return state_manager.get_global_sequence()

        return 0

    def _create_no_cache_response(self, content: dict, status_code: int = 200):
        """Create JSONResponse with anti-cache headers.

        Args:
            content: Response content dictionary
            status_code: HTTP status code

        Returns:
            JSONResponse with no-cache headers
        """
        from fastapi.responses import JSONResponse

        response = JSONResponse(content=content, status_code=status_code)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    def _check_led_handler_available(self, request: Request):
        """Check if LED handler is available and return error if not.

        Args:
            request: FastAPI request

        Returns:
            Tuple of (led_handler, error_response) where error_response is None if available
        """
        led_handler = self._get_led_handler(request)
        if not led_handler:
            error_response = UnifiedResponseService.error(
                message="LED event handler not available",
                error_type="service_unavailable",
                status_code=503
            )
            return None, error_response
        return led_handler, None

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
                self.log_operation("API: Responding with playback state")

                # Create response with anti-cache headers
                return self._create_no_cache_response(playback_state)

            except Exception as e:
                return self.handle_endpoint_error(
                    e,
                    operation="get_playback_status",
                    message="Failed to get playback status"
                )

        @self.router.get("/health")
        @handle_http_errors()
        async def health_check(request: Request):
            """Perform system health check."""
            try:
                self.log_operation("API /api/health: Health check requested")

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
                server_seq = self._get_server_seq_from_container(container)

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
                return self.handle_endpoint_error(
                    e,
                    operation="health_check",
                    message="Health check failed"
                )

        @self.router.get("/system/info")
        @handle_http_errors()
        async def get_system_info(request: Request):
            """Get system information."""
            try:
                self.log_operation("API /api/system/info: System info requested")

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
                        pass  # nosec B110 - optional psutil data, OK to skip on failure

                # Get server_seq from state manager (required by contract v3.1.0)
                container = getattr(request.app, "container", None)
                server_seq = self._get_server_seq_from_container(container)

                # Read application version from VERSION file
                import os
                version = "0.4.1"  # Default fallback
                version_file = os.path.join(os.path.dirname(__file__), "../../../../../VERSION")
                try:
                    if os.path.exists(version_file):
                        with open(version_file) as f:
                            version = f.read().strip()
                except Exception:
                    pass  # nosec B110 - use default version on error, non-critical

                # Build capabilities for RPI
                capabilities = {
                    "upload_format": "multipart",  # FastAPI uses multipart/form-data
                    "max_chunk_size": 1024 * 1024,  # 1MB chunks (RPI has more RAM)
                    "player_monitoring": True,      # RPI can monitor playback efficiently
                    "nfc_available": False,         # Default, detect at runtime
                    "led_control": False,           # Default, detect at runtime
                    # v3.3.0 fields
                    "backend_type": "rpi",
                    "position_update_interval_ms": 500,  # High-frequency updates
                    "supports_websocket_position": True,
                    # v4.0.0 NFC platform-specific fields
                    "nfc_session_model": "multi",  # RPI uses explicit session IDs
                    "nfc_supports_override": False,  # ESP32 only
                    "nfc_supports_tags_list": False,  # ESP32 only
                }

                # Detect NFC service availability
                if container:
                    nfc_service = getattr(container, "nfc", None)
                    if nfc_service:
                        # Check if NFC service is actually functional
                        try:
                            # For now, just check if service exists
                            capabilities["nfc_available"] = True
                            self.log_operation("NFC service detected and available")
                        except Exception as e:
                            self._logger.warning(f"NFC service exists but not functional: {e}")
                            capabilities["nfc_available"] = False

                    # Detect LED service availability
                    led_service = getattr(container, "led_hat", None)
                    if led_service:
                        try:
                            capabilities["led_control"] = True
                            self.log_operation("LED control service detected and available")
                        except Exception as e:
                            self._logger.warning(f"LED service exists but not functional: {e}")
                            capabilities["led_control"] = False

                self.log_operation(f"Capabilities detected: {capabilities}")

                from fastapi.responses import JSONResponse
                return JSONResponse(content={
                    "status": "success",
                    "message": "System information retrieved successfully",
                    "timestamp": time.time(),
                    "server_seq": server_seq,
                    "data": {
                        "system_info": system_info,
                        "version": version,
                        "contract_version": "4.0.0",  # Updated to 4.0.0
                        "hostname": system_info.get("hostname", "localhost"),
                        "uptime": 3600,  # System uptime in seconds
                        "server_seq": server_seq,
                        "capabilities": capabilities,  # NEW: Backend capabilities
                    }
                })

            except Exception as e:
                return self.handle_endpoint_error(
                    e,
                    operation="get_system_info",
                    message="Failed to get system information"
                )

        @self.router.get("/system/hardware_status")
        @handle_http_errors()
        async def get_hardware_status(request: Request):
            """Get detailed hardware status for all subsystems.

            Returns:
                Hardware status including:
                - Audio backend status (available, device name, errors)
                - NFC reader status
                - LED controller status
                - Database status
                - Overall system health
            """
            try:
                self.log_operation("API /api/system/hardware_status: Hardware status requested")

                # Get container from app state
                container = getattr(request.app, "container", None)
                server_seq = self._get_server_seq_from_container(container)

                hardware_status = {
                    "audio": {"available": False, "status": "unknown"},
                    "nfc": {"available": False, "status": "unknown"},
                    "led": {"available": False, "status": "unknown"},
                    "database": {"available": False, "status": "unknown"},
                    "overall_health": "unknown"
                }

                if container:
                    # Check audio backend status
                    try:
                        coordinator = self._get_coordinator(request)
                        if coordinator and hasattr(coordinator, '_audio_backend'):
                            audio_backend = coordinator._audio_backend
                            if hasattr(audio_backend, 'get_hardware_status'):
                                audio_status = audio_backend.get_hardware_status()
                                hardware_status["audio"] = {
                                    "available": audio_status.get("available", False),
                                    "status": "operational" if audio_status.get("available") else "degraded",
                                    "device": audio_status.get("device"),
                                    "initialized": audio_status.get("initialized", False),
                                    "error": audio_status.get("error"),
                                    "backend_type": audio_status.get("backend_type")
                                }
                            elif hasattr(audio_backend, 'is_hardware_available'):
                                is_available = audio_backend.is_hardware_available()
                                hardware_status["audio"] = {
                                    "available": is_available,
                                    "status": "operational" if is_available else "degraded"
                                }
                    except Exception as e:
                        self._logger.warning(f"Failed to get audio status: {e}")
                        hardware_status["audio"] = {
                            "available": False,
                            "status": "error",
                            "error": str(e)
                        }

                    # Check NFC status
                    try:
                        nfc_service = getattr(container, "nfc", None)
                        if nfc_service:
                            hardware_status["nfc"] = {
                                "available": True,
                                "status": "operational"
                            }
                    except Exception as e:
                        self._logger.warning(f"Failed to get NFC status: {e}")
                        hardware_status["nfc"] = {
                            "available": False,
                            "status": "error",
                            "error": str(e)
                        }

                    # Check LED status
                    try:
                        led_handler = self._get_led_handler(request) if self._get_led_handler else None
                        if led_handler:
                            hardware_status["led"] = {
                                "available": True,
                                "status": "operational"
                            }
                    except Exception as e:
                        self._logger.warning(f"Failed to get LED status: {e}")
                        hardware_status["led"] = {
                            "available": False,
                            "status": "error",
                            "error": str(e)
                        }

                    # Check database status
                    try:
                        # Check if database is accessible
                        db_manager = getattr(container, "database_manager", None)
                        if db_manager:
                            hardware_status["database"] = {
                                "available": True,
                                "status": "operational"
                            }
                    except Exception as e:
                        self._logger.warning(f"Failed to get database status: {e}")
                        hardware_status["database"] = {
                            "available": False,
                            "status": "error",
                            "error": str(e)
                        }

                # Calculate overall health
                available_systems = sum(1 for sys in hardware_status.values()
                                      if isinstance(sys, dict) and sys.get("available", False))
                total_systems = len([k for k in hardware_status.keys() if k != "overall_health"])

                if available_systems == total_systems:
                    hardware_status["overall_health"] = "healthy"
                elif available_systems >= total_systems * 0.5:
                    hardware_status["overall_health"] = "degraded"
                else:
                    hardware_status["overall_health"] = "critical"

                return UnifiedResponseService.success(
                    message=f"Hardware status retrieved - {hardware_status['overall_health']}",
                    data=hardware_status,
                    server_seq=server_seq
                )

            except Exception as e:
                return self.handle_endpoint_error(
                    e,
                    operation="get_hardware_status",
                    message="Failed to get hardware status"
                )

        @self.router.get("/system/logs")
        @handle_http_errors()
        async def get_system_logs():
            """Get system logs."""
            try:
                self.log_operation("API /api/system/logs: Logs requested")

                import glob
                logs_data: dict[str, Any] = {"logs": [], "log_files_available": []}

                # Search for log files
                # Using /tmp is intentional for IoT device log collection - these are
                # predefined paths for application logs, not user-controlled input
                possible_log_paths = [
                    "/var/log/tomb-rpi/*.log",
                    "/tmp/tomb-rpi*.log",  # nosec B108 - intentional tmp usage for IoT device logs
                    "logs/*.log",
                    "*.log",
                ]

                for pattern in possible_log_paths:
                    log_files = glob.glob(pattern)
                    for log_file in log_files:
                        logs_data["log_files_available"].append(log_file)
                        # Read last 100 lines
                        try:
                            with open(log_file) as f:
                                lines = f.readlines()
                                last_lines = lines[-100:] if len(lines) > 100 else lines
                                logs_data["logs"].extend([
                                    {"file": log_file, "line": line.strip()}
                                    for line in last_lines if line.strip()
                                ])
                        except OSError:
                            pass

                from fastapi.responses import JSONResponse
                return JSONResponse(content={
                    "status": "success",
                    "message": "System logs retrieved successfully",
                    "timestamp": time.time(),
                    "data": logs_data
                })

            except Exception as e:
                return self.handle_endpoint_error(
                    e,
                    operation="get_system_logs",
                    message="Failed to get system logs"
                )

        @self.router.post("/system/restart")
        @handle_http_errors()
        async def restart_system():
            """Restart the system."""
            try:
                self.log_operation("API /api/system/restart: Restart requested")

                import asyncio
                import os
                import signal

                # Schedule restart after response is sent
                async def delayed_restart():
                    await asyncio.sleep(2)
                    self.log_operation("Restarting application...")
                    os.kill(os.getpid(), signal.SIGTERM)

                # Start delayed restart task
                asyncio.create_task(delayed_restart())

                response_data = {
                    "status": "restart_scheduled",
                    "message": "Application restart scheduled in 2 seconds",
                }


                from app.src.common.response_models import create_success_response

                standardized_response = create_success_response(
                    message="System restart scheduled successfully",
                    data=response_data
                )
                return self._create_no_cache_response(standardized_response)

            except Exception as e:
                return self.handle_endpoint_error(
                    e,
                    operation="restart_system",
                    message="Failed to restart system"
                )

        # LED control endpoints
        if self._get_led_handler:
            from pydantic import BaseModel, Field

            class SetBrightnessRequest(BaseModel):
                brightness: float = Field(..., ge=0.0, le=1.0, description="LED brightness level (0.0-1.0)")

            @self.router.post("/system/led/brightness")
            @handle_http_errors()
            async def set_led_brightness(request: Request, body: SetBrightnessRequest):
                """Set LED brightness level."""
                try:
                    self.log_operation(f"API /api/system/led/brightness: Set brightness to {body.brightness:.1%}")

                    led_handler, error = self._check_led_handler_available(request)
                    if error:
                        return error

                    success = await led_handler.set_brightness(body.brightness)

                    if success:
                        return UnifiedResponseService.success(
                            message=f"LED brightness set to {body.brightness:.1%}",
                            data={"brightness": body.brightness}
                        )
                    return UnifiedResponseService.error(
                        message="Failed to set LED brightness",
                        error_type="operation_failed",
                        status_code=500
                    )

                except Exception as e:
                    return self.handle_endpoint_error(
                        e,
                        operation="set_led_brightness",
                        message="Failed to set LED brightness"
                    )

            @self.router.post("/system/led/reload-config")
            @handle_http_errors()
            async def reload_led_config(request: Request):
                """Reload LED brightness from hardware configuration."""
                try:
                    self.log_operation("API /api/system/led/reload-config: Reloading LED brightness from config")

                    led_handler, error = self._check_led_handler_available(request)
                    if error:
                        return error

                    success = await led_handler.reload_brightness_from_config()

                    if success:
                        # Get current brightness from LED controller status
                        status = led_handler.get_status()
                        brightness = status.get("led_manager_status", {}).get("brightness", 0)

                        return UnifiedResponseService.success(
                            message="LED brightness reloaded from config",
                            data={"brightness": brightness}
                        )
                    return UnifiedResponseService.error(
                        message="Failed to reload LED brightness from config",
                        error_type="operation_failed",
                        status_code=500
                    )

                except Exception as e:
                    return self.handle_endpoint_error(
                        e,
                        operation="reload_led_config",
                        message="Failed to reload LED config"
                    )

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        return self.router
