# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
State Manager Lifecycle Service (DDD Architecture)

Single responsibility: Manages background tasks and cleanup for state management components.
Clean separation following Domain-Driven Design principles.
"""

import asyncio
import time
from typing import Any, Dict, Optional
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.services.operation_tracker import OperationTracker
from app.src.services.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


class StateManagerLifecycleApplicationService:
    """
    Manages lifecycle and cleanup tasks for state management components.

    Single Responsibility: Background task coordination and cleanup management.

    Responsibilities:
    - Periodic cleanup task management
    - Component health monitoring
    - Lifecycle coordination for state management services
    - Metrics collection and reporting

    Does NOT handle:
    - Event broadcasting (delegated to StateEventCoordinator)
    - State storage (delegated to PlaybackStateManager)
    - Business logic (handled by application services)
    """

    def __init__(
        self,
        operation_tracker: OperationTracker = None,
        event_outbox: EventOutbox = None,
        cleanup_interval: int = 300,  # 5 minutes
    ):
        """Initialize state manager lifecycle service.

        Args:
            operation_tracker: Operation tracker for cleanup
            event_outbox: Event outbox for cleanup
            cleanup_interval: Cleanup interval in seconds
        """
        self.operation_tracker = operation_tracker or OperationTracker()
        self.event_outbox = event_outbox or EventOutbox()
        self.cleanup_interval = cleanup_interval

        # Task management
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info(
            f"StateManagerLifecycleService initialized with cleanup interval: {cleanup_interval}s"
        )

    async def start_lifecycle_management(self) -> None:
        """Start background lifecycle management tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("Lifecycle management already running")
            return

        logger.info("Starting state manager lifecycle management")
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_lifecycle_management(self) -> None:
        """Stop background lifecycle management tasks."""
        if not self._cleanup_task:
            logger.warning("No lifecycle management task to stop")
            return

        logger.info("Stopping state manager lifecycle management")
        self._is_running = False

        # Cancel and wait for cleanup task
        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup_task = None
            logger.info("Lifecycle management stopped")

    @handle_service_errors("state_manager_lifecycle_service")
    async def _cleanup_loop(self) -> None:
        """Internal cleanup loop that runs periodically."""
        logger.info("State manager cleanup loop started")

        while self._is_running:
            try:
                # Perform cleanup operations
                await self._perform_cleanup()

                # Log metrics periodically (every hour)
                if time.time() % 3600 < self.cleanup_interval:
                    metrics = await self.get_health_metrics()
                    logger.info(f"State management metrics: {metrics}")

                # Sleep before next cleanup cycle
                await asyncio.sleep(self.cleanup_interval)

            except asyncio.CancelledError:
                logger.info("State manager cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in state manager cleanup loop: {e}")
                # Continue after error, but still sleep to prevent tight loops
                await asyncio.sleep(self.cleanup_interval)

        logger.info("State manager cleanup loop ended")

    @handle_service_errors("state_manager_lifecycle_service")
    async def _perform_cleanup(self) -> None:
        """Perform cleanup operations on managed components."""
        cleanup_stats = {
            "operations_cleaned": 0,
            "outbox_processed": False,
        }

        try:
            # Clean up expired operations
            if self.operation_tracker:
                cleaned_ops = await self.operation_tracker.cleanup_expired_operations()
                cleanup_stats["operations_cleaned"] = cleaned_ops

            # Process event outbox to handle any failed events
            if self.event_outbox:
                await self.event_outbox.process_outbox()
                cleanup_stats["outbox_processed"] = True

            # Log cleanup results if significant activity
            if cleanup_stats["operations_cleaned"] > 0:
                logger.debug(
                    f"Cleanup completed: {cleanup_stats['operations_cleaned']} operations cleaned"
                )

        except Exception as e:
            logger.error(f"Error during cleanup operations: {e}")

    async def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics from managed components.

        Returns:
            Dictionary containing health metrics from all managed components
        """
        metrics = {
            "lifecycle_service": {
                "is_running": self._is_running,
                "cleanup_task_running": self._cleanup_task is not None and not self._cleanup_task.done(),
                "cleanup_interval": self.cleanup_interval,
            }
        }

        try:
            # Get operation tracker metrics
            if self.operation_tracker:
                metrics["operations"] = self.operation_tracker.get_stats()

            # Get event outbox metrics
            if self.event_outbox:
                metrics["outbox"] = self.event_outbox.get_stats()

        except Exception as e:
            logger.error(f"Error collecting health metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    async def force_cleanup(self) -> Dict[str, Any]:
        """Force immediate cleanup of all managed components.

        Returns:
            Dictionary containing cleanup results
        """
        logger.info("Forcing immediate cleanup of state management components")

        cleanup_results = {
            "timestamp": time.time(),
            "operations_cleaned": 0,
            "outbox_processed": False,
        }

        try:
            await self._perform_cleanup()
            cleanup_results["success"] = True
            cleanup_results["message"] = "Forced cleanup completed successfully"

        except Exception as e:
            cleanup_results["success"] = False
            cleanup_results["message"] = f"Forced cleanup failed: {e}"
            logger.error(f"Forced cleanup failed: {e}")

        return cleanup_results

    def is_running(self) -> bool:
        """Check if lifecycle management is currently running."""
        return self._is_running

    async def get_status(self) -> Dict[str, Any]:
        """Get current status of lifecycle service.

        Returns:
            Dictionary containing current status information
        """
        return {
            "is_running": self._is_running,
            "cleanup_task_active": self._cleanup_task is not None and not self._cleanup_task.done(),
            "cleanup_interval": self.cleanup_interval,
            "has_operation_tracker": self.operation_tracker is not None,
            "has_event_outbox": self.event_outbox is not None,
        }
