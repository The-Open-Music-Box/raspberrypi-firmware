# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Configuration for the unified monitoring system."""

from typing import Optional


class MonitoringConfig:
    """Centralized configuration for all monitoring components.

    Uses dependency injection to get app config.
    """

    def __init__(self, app_config=None):
        """Initialize monitoring config with app config injection.

        Args:
            app_config: AppConfig instance. Required for proper initialization.
        """
        if app_config is None:
            # For backward compatibility during transition, create a new instance
            from app.src.config.app_config import AppConfig
            app_config = AppConfig()
        self._app_config = app_config

    def _get_config(self):
        """Get the app config."""
        return self._app_config

    @property
    def debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self._get_config().debug

    @property
    def event_monitoring_enabled(self) -> bool:
        """Check if event monitoring is enabled (only in debug mode)."""
        return self._get_config().enable_event_monitoring

    @property
    def performance_monitoring_enabled(self) -> bool:
        """Check if performance monitoring is enabled."""
        return self._get_config().enable_performance_monitoring

    @property
    def file_logging_enabled(self) -> bool:
        """Check if file logging is enabled."""
        return self._get_config().log_file is not None

    @property
    def trace_history_size(self) -> int:
        """Get maximum events to keep in trace history."""
        return self._get_config().monitoring_trace_history_size

    @property
    def monitoring_file_logging_enabled(self) -> bool:
        """Check if monitoring-specific file logging is enabled."""
        return self._get_config().monitoring_file_logging

    @property
    def log_level(self) -> str:
        """Get the configured log level."""
        return self._get_config().log_level

    @property
    def log_format(self) -> str:
        """Get the configured log format."""
        return self._get_config().log_format

    @property
    def log_file_path(self) -> Optional[str]:
        """Get the log file path."""
        return self._get_config().log_file

    def should_monitor_component(self, component_name: str) -> bool:
        """Check if a specific component should be monitored.

        Args:
            component_name: Name of the component to check

        Returns:
            True if component should be monitored, False otherwise
        """
        if not self.debug_mode:
            return False

        # Component-specific monitoring rules
        component_rules = {
            "audio_engine": self.event_monitoring_enabled,
            "playlist_manager": self.event_monitoring_enabled,
            "event_bus": self.event_monitoring_enabled,
            "performance": self.performance_monitoring_enabled,
        }

        return component_rules.get(component_name, self.event_monitoring_enabled)


# Removed Global Instance
# monitoring_config global instance has been removed in favor of dependency injection
# Use: container.get("monitoring_config") or get_monitoring_config()
# Migration completed: All code now uses DI
