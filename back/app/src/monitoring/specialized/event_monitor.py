# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Minimal EventMonitor stub to avoid cross-layer imports.

This stub maintains API shape but does not subscribe to domain events.
"""

import importlib as _il
_logging = _il.import_module('logging')
from typing import Optional


class EventMonitor:
    """Minimal stub for event monitoring (no cross-layer imports)."""

    def __init__(self, max_trace_history: int = 1000, enable_file_logging: bool = False):
        self._is_active = False
        _logging.getLogger(__name__).info("📊 EventMonitor initialized (stub)")

    async def handle_event(self, event) -> None:  # pragma: no cover - stub
        return

    def shutdown(self) -> None:
        self._is_active = False
        _logging.getLogger(__name__).info("📊 EventMonitor shutdown")

    def get_monitoring_statistics(self) -> dict:
        return {"active": self._is_active, "stub": True}

        finally:
            # Track monitoring overhead
            monitor_time = (time.time() - monitor_start_time) * 1000
            self._monitoring_overhead_ms += monitor_time

    async def _process_event(self, event: AudioEvent) -> None:
        """Process specific event types for detailed monitoring."""
        if not EVENT_BUS_AVAILABLE:
            return

        event_type = type(event)

        # Handle specific event types if available
        try:
            if hasattr(event, "file_path") and hasattr(event, "duration_ms"):
                # Track/Playlist events
                await self._handle_track_event(event)
            elif hasattr(event, "old_state") and hasattr(event, "new_state"):
                # State change events
                await self._handle_state_changed(event)
            elif hasattr(event, "error_type"):
                # Error events
                await self._handle_error_event(event)
            elif hasattr(event, "old_volume") and hasattr(event, "new_volume"):
                # Volume events
                await self._handle_volume_event(event)
        except Exception as e:
            logger.error(f"📊 Error processing event: {e}")

    async def _handle_track_event(self, event) -> None:
        """Handle track-related events."""
        try:
            file_name = Path(event.file_path).name if hasattr(event, "file_path") else "unknown"
            duration_s = event.duration_ms / 1000 if hasattr(event, "duration_ms") else 0

            if "Started" in type(event).__name__:
                logger.debug(f"📊 Track started: {file_name} ({duration_s:.1f}s)")
            elif "Ended" in type(event).__name__:
                completion = 0
                if (
                    hasattr(event, "position_ms")
                    and hasattr(event, "duration_ms")
                    and event.duration_ms > 0
                ):
                    completion = (event.position_ms / event.duration_ms) * 100
                reason = getattr(event, "reason", "unknown")
                logger.debug(
                    f"📊 Track ended: {file_name} ({completion:.1f}% complete, reason: {reason})"
                )
        except Exception as e:
            logger.error(f"📊 Error handling track event: {e}")

    async def _handle_state_changed(self, event) -> None:
        """Handle state change events."""
        try:
            old_state = getattr(event, "old_state", "unknown")
            new_state = getattr(event, "new_state", "unknown")
            position_ms = getattr(event, "position_ms", 0)

            logger.debug(
                f"📊 State transition: {old_state} -> {new_state} at {position_ms/1000:.1f}s"
            )
        except Exception as e:
            logger.error(f"📊 Error handling state change event: {e}")

    async def _handle_error_event(self, event) -> None:
        """Handle error events."""
        try:
            error_type = getattr(event, "error_type", "unknown")
            error_message = getattr(event, "error_message", "unknown")

            logger.warning(f"📊 Error detected: {error_type} - {error_message}")
        except Exception as e:
            logger.error(f"📊 Error handling error event: {e}")

    async def _handle_volume_event(self, event) -> None:
        """Handle volume change events."""
        try:
            old_volume = getattr(event, "old_volume", 0)
            new_volume = getattr(event, "new_volume", 0)
            muted = getattr(event, "muted", False)

            logger.debug(f"📊 Volume changed: {old_volume} -> {new_volume} (muted: {muted})")
        except Exception as e:
            logger.error(f"📊 Error handling volume event: {e}")

    def _update_event_metrics(
        self, event_type: str, processing_time_ms: float, is_error: bool = False
    ) -> None:
        """Update metrics for an event type."""
        current_time = time.time()

        if event_type not in self._event_metrics:
            self._event_metrics[event_type] = EventMetrics(
                event_type=event_type, first_seen=current_time
            )

        metrics = self._event_metrics[event_type]
        metrics.count += 1
        metrics.last_seen = current_time
        metrics.total_processing_time_ms += processing_time_ms
        metrics.average_processing_time_ms = metrics.total_processing_time_ms / metrics.count
        metrics.min_processing_time_ms = min(metrics.min_processing_time_ms, processing_time_ms)
        metrics.max_processing_time_ms = max(metrics.max_processing_time_ms, processing_time_ms)

        if is_error:
            metrics.error_count += 1

    def _extract_event_metadata(self, event: AudioEvent) -> Dict[str, Any]:
        """Extract relevant metadata from event for tracing."""
        metadata = {"timestamp": getattr(event, "timestamp", time.time())}

        # Add common event attributes if present
        for attr in [
            "file_path",
            "duration_ms",
            "position_ms",
            "old_state",
            "new_state",
            "old_volume",
            "new_volume",
            "muted",
            "error_type",
            "error_message",
            "reason",
        ]:
            if hasattr(event, attr):
                metadata[attr] = getattr(event, attr)

        return metadata

    async def _log_event_to_file(self, trace: EventTrace) -> None:
        """Log event trace to file."""
        if not self._log_file_path:
            return

        try:
            log_entry = {
                "timestamp": trace.timestamp,
                "event_id": trace.event_id,
                "event_type": trace.event_type,
                "source_component": trace.source_component,
                "processing_time_ms": trace.processing_time_ms,
                "success": trace.success,
                "error_message": trace.error_message,
                "metadata": trace.metadata,
            }

            # Append to JSONL file
            with open(self._log_file_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

        except Exception as e:
            logger.warning(f"📊 Failed to log event to file: {e}")

    async def _check_alerts(self, event_type: str, processing_time_ms: float) -> None:
        """Check for alert conditions."""
        # Check processing time threshold
        if processing_time_ms > self._alert_thresholds["max_processing_time_ms"]:
            logger.warning(
                f"📊 ALERT: Slow event processing - {event_type} took {processing_time_ms:.1f}ms"
            )

        # Check error rate
        if event_type in self._event_metrics:
            metrics = self._event_metrics[event_type]
            error_rate = metrics.error_count / metrics.count

            if error_rate > self._alert_thresholds["error_rate_threshold"]:
                logger.warning(f"📊 ALERT: High error rate for {event_type}: {error_rate:.2%}")

        # Check queue size if event bus is available
        if EVENT_BUS_AVAILABLE:
            try:
                queue_size = audio_event_bus.get_statistics().get("queue_size", 0)
                if queue_size > self._alert_thresholds["queue_size_threshold"]:
                    logger.warning(f"📊 ALERT: Large event queue size: {queue_size}")
            except Exception:
                pass  # Event bus statistics not available

    # === Public API ===

    @property
    def is_active(self) -> bool:
        """Check if event monitoring is currently active."""
        return self._is_active

    def get_event_metrics(self) -> Dict[str, EventMetrics]:
        """Get event metrics for all monitored event types."""
        return self._event_metrics.copy()

    def get_recent_events(self, count: int = 50) -> List[EventTrace]:
        """Get recent event traces."""
        return list(self._event_trace_history)[-count:]

    def get_events_by_type(self, event_type: str, count: int = 50) -> List[EventTrace]:
        """Get recent events of a specific type."""
        filtered = [trace for trace in self._event_trace_history if trace.event_type == event_type]
        return filtered[-count:]

    def get_error_events(self, count: int = 50) -> List[EventTrace]:
        """Get recent error events."""
        errors = [trace for trace in self._event_trace_history if not trace.success]
        return errors[-count:]

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics."""
        total_processing_time = sum(
            m.total_processing_time_ms for m in self._event_metrics.values()
        )
        total_events = sum(m.count for m in self._event_metrics.values())
        total_errors = sum(m.error_count for m in self._event_metrics.values())

        # Calculate average monitoring overhead per event
        avg_overhead = self._monitoring_overhead_ms / max(self._total_events_monitored, 1)

        return {
            "is_active": self._is_active,
            "monitoring_enabled": monitoring_config.event_monitoring_enabled,
            "event_bus_available": EVENT_BUS_AVAILABLE,
            "total_events_monitored": self._total_events_monitored,
            "total_processing_time_ms": total_processing_time,
            "average_processing_time_ms": total_processing_time / max(total_events, 1),
            "total_errors": total_errors,
            "error_rate": total_errors / max(total_events, 1),
            "monitoring_overhead_ms": self._monitoring_overhead_ms,
            "average_monitoring_overhead_ms": avg_overhead,
            "event_types_monitored": len(self._event_metrics),
            "trace_history_size": len(self._event_trace_history),
            "active_events": len(self._active_events),
            "file_logging_enabled": self._enable_file_logging,
            "log_file_path": str(self._log_file_path) if self._log_file_path else None,
        }

    def set_event_filter(self, event_types: Set[str]) -> None:
        """Set event type filter for monitoring."""
        self._event_type_filters = event_types
        logger.info(f"📊 Event filter updated: {event_types}")

    def clear_event_filter(self) -> None:
        """Clear event type filter."""
        self._event_type_filters.clear()
        logger.info("📊 Event filter cleared")

    def set_alert_threshold(self, threshold_name: str, value: float) -> None:
        """Set alert threshold."""
        if threshold_name in self._alert_thresholds:
            self._alert_thresholds[threshold_name] = value
            logger.info(f"📊 Alert threshold updated: {threshold_name} = {value}")
        else:
            logger.warning(f"📊 Unknown alert threshold: {threshold_name}")

    def reset_metrics(self) -> None:
        """Reset all metrics and trace history."""
        self._event_metrics.clear()
        self._event_trace_history.clear()
        self._active_events.clear()
        self._monitoring_overhead_ms = 0.0
        self._total_events_monitored = 0

        logger.info("📊 Event monitor metrics reset")

    async def generate_report(self, include_traces: bool = False) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        report = {
            "timestamp": time.time(),
            "monitoring_statistics": self.get_monitoring_statistics(),
            "event_metrics": {
                event_type: asdict(metrics) for event_type, metrics in self._event_metrics.items()
            },
            "recent_errors": [asdict(trace) for trace in self.get_error_events(10)],
            "alert_thresholds": self._alert_thresholds.copy(),
            "configuration": {
                "debug_mode": monitoring_config.debug_mode,
                "event_monitoring_enabled": monitoring_config.event_monitoring_enabled,
                "file_logging_enabled": monitoring_config.file_logging_enabled,
            },
        }

        if EVENT_BUS_AVAILABLE:
            try:
                report["event_bus_statistics"] = audio_event_bus.get_statistics()
            except Exception:
                report["event_bus_statistics"] = {"error": "Statistics unavailable"}

        if include_traces:
            report["recent_event_traces"] = [asdict(trace) for trace in self.get_recent_events(100)]

        return report

    def shutdown(self):
        """Shutdown the event monitor."""
        self._deactivate_monitoring()
        self._event_metrics.clear()
        self._event_trace_history.clear()
        self._active_events.clear()
        logger.info("📊 EventMonitor shut down")


# ❌ REMOVED: Global instance creation (now handled by factory)
# event_monitor = EventMonitor(max_trace_history=1000, enable_file_logging=False)
