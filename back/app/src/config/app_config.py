# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified configuration system for TheOpenMusicBox application.

Loads settings exclusively from .env file and provides centralized configuration for all
modules.
"""

import logging
import os
from pathlib import Path
from typing import Any, List

from dotenv import load_dotenv
from app.src.config.audio_config import AudioConfig
from app.src.config.hardware_config import HardwareConfig
from app.src.config.nfc_config import NFCConfig

logger = logging.getLogger(__name__)


class AppConfig:
    """
    Unified configuration class for TheOpenMusicBox application.

    This class loads ALL configuration from .env file - no default values.
    The .env file is the single source of truth for all configuration.

    Usage:
        from app.src.config import config
        db_path = config.db_file
    """

    # Required configuration keys that must be present in .env
    REQUIRED_KEYS = [
        "debug",
        "use_reloader",
        "socketio_host",
        "socketio_port",
        "upload_folder",
        "db_file",
        "cors_allowed_origins",
        "log_level",
        "log_format",
        "log_file",
        "use_mock_hardware",
        "app_module",
        "uvicorn_reload",
        "upload_allowed_extensions",
        "upload_max_size",
        "mdns_service_type",
        "mdns_service_path",
        "mdns_service_version",
        "mdns_service_friendly_name",
        "feature_legacy_playlists_snapshot",
        "enable_event_monitoring",
        "enable_performance_monitoring",
        "monitoring_trace_history_size",
        "monitoring_file_logging",
    ]

    def __init__(self):
        """
        Initialize the configuration with values from .env file only.
        No default values - .env must contain all required settings.
        """
        self._values = {}
        self._load_environment()
        self._validate_required_keys()
        self._validate_directories()

        # Initialize sub-configurations
        self.audio = AudioConfig()
        self.hardware = HardwareConfig()
        self.nfc = NFCConfig()

        # Override sub-config values from environment if present
        self._load_subconfig_overrides()

        # Validate all configurations
        self._validate_configs()

    def _validate_required_keys(self) -> None:
        """
        Validate that all required configuration keys are present.
        """
        missing_keys = []
        for key in self.REQUIRED_KEYS:
            if key not in self._values or self._values[key] is None:
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(
                f"Missing required configuration keys in .env file: {', '.join(missing_keys)}"
            )

    def _load_environment(self) -> None:
        """
        Load configuration from .env file and environment variables.
        The .env file is mandatory - no default values are provided.
        """
        # Try multiple possible locations for .env file
        possible_paths = [
            # Development: /back/.env (when running from /back/)
            Path(__file__).parent.parent.parent.parent / ".env",
            # Production: /.env (when running from project root)
            Path(__file__).parent.parent.parent / ".env",
            # Fallback: current working directory
            Path.cwd() / ".env",
        ]

        env_path = None
        for path in possible_paths:
            if path.exists():
                env_path = path
                break

        if not env_path:
            paths_checked = "\n".join([f"  - {p}" for p in possible_paths])
            raise FileNotFoundError(
                f"Configuration file not found in any of these locations:\n{paths_checked}\n"
                f"The .env file is required as the single source of truth for configuration."
            )

        load_dotenv(env_path)
        logger.info("Loaded configuration from %s", env_path)

        # Load all configuration values from environment variables
        for key in self.REQUIRED_KEYS:
            env_key = key.upper()
            if env_key in os.environ:
                # Detect type from environment value
                env_value = os.environ[env_key]
                self._values[key] = self._convert_env_value(env_value)
                logger.debug("Loaded %s=%s from environment", key, self._values[key])

    def _validate_directories(self) -> None:
        """
        Ensure required directories exist.
        """
        # Get the app directory path (parent of src)
        app_dir = Path(__file__).parent.parent.parent

        # Use property methods to get the fully resolved paths
        # This ensures we use the same logic as the rest of the application

        # Handle upload folder
        upload_path = Path(self.upload_folder)
        if not upload_path.is_absolute():
            upload_path = app_dir / upload_path
        upload_path.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Config paths: uploads=%s", upload_path)

        # Handle database file - create its parent directory
        db_path = Path(self.db_file)
        if not db_path.is_absolute():
            db_path = app_dir / db_path
        db_dir = db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Config paths: db=%s", db_dir)

        # Ensure log directory exists
        log_path = Path(self.log_file)
        if not log_path.is_absolute():
            log_path = app_dir / log_path
        log_dir = log_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)

    def _convert_env_value(self, value: str) -> Any:
        """
        Convert string environment variable to the appropriate type.
        Auto-detects type based on common patterns.

        Args:
            value: String value from environment

        Returns:
            Converted value with auto-detected type
        """
        if not isinstance(value, str):
            return value

        # Remove quotes if present
        value = value.strip("'\"")

        try:
            # Boolean detection
            if value.lower() in ("true", "false", "t", "f", "yes", "no", "1", "0"):
                return value.lower() in ("true", "t", "yes", "1")

            # Integer detection
            if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                return int(value)

            # Float detection
            if "." in value:
                try:
                    return float(value)
                except ValueError:
                    pass

            # List detection (semicolon separated)
            if ";" in value:
                return value.split(";")

            # Default: return as string
            return value

        except (ValueError, TypeError) as e:
            logger.error("Error converting value '%s': %s", value, e)
            return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:     key: Configuration key     default: Default value if key doesn't exist

        Returns:     Configuration value or default
        """
        return self._values.get(key, default)

    def __getattr__(self, name: str) -> Any:
        """
        Access configuration values as attributes.

        Args:     name: Attribute name

        Returns:     Configuration value

        Raises:     AttributeError: If configuration key doesn't exist
        """
        # Support both hardware and hardware_config for compatibility
        if name == "hardware_config":
            return self.hardware
        if name in self._values:
            return self._values[name]
        raise AttributeError(f"Configuration has no attribute '{name}'")

    @property
    def debug(self) -> bool:
        """
        Whether debug mode is enabled.
        """
        return self._values.get("debug", False)

    @property
    def use_reloader(self) -> bool:
        """
        Whether to use auto-reloader.
        """
        return self._values.get("use_reloader", False)

    @property
    def socketio_host(self) -> str:
        """
        Host for Socket.IO server.
        """
        return self._values.get("socketio_host", "0.0.0.0")

    @property
    def socketio_port(self) -> int:
        """
        Port for Socket.IO server (required).
        """
        value = self._values.get("socketio_port")
        if value is None:
            raise ValueError(
                "Critical config missing: 'socketio_port' must be set in config/environment."
            )
        return int(value)

    @property
    def upload_folder(self) -> str:
        """
        Directory for uploaded files (required).

        Returns the absolute path to the upload folder, ensuring it resolves correctly
        regardless of the working directory at runtime.
        """
        value = self._values.get("upload_folder")
        if not value:
            raise ValueError(
                "Critical config missing: 'upload_folder' must be set in config/environment."
            )

        # Get the app directory path (parent of src)
        app_dir = Path(__file__).parent.parent.parent

        # If value is a relative path, make it absolute from app_dir
        path = Path(value)
        if not path.is_absolute():
            path = app_dir / path

        # Log the absolute path for debugging
        logger.debug("Resolved upload_folder path: %s", path)

        return str(path)

    @property
    def upload_allowed_extensions(self) -> List[str]:
        """
        List of allowed upload extensions.
        """
        value = self._values.get("upload_allowed_extensions", "")
        return value.split(";") if isinstance(value, str) else value

    @property
    def upload_max_size(self) -> int:
        """
        Maximum upload file size in bytes.
        """
        value = self._values.get("upload_max_size")
        if value is None:
            raise ValueError(
                "Critical config missing: 'upload_max_size' must be set in config/environment."
            )
        return int(value)

    @property
    def cors_allowed_origins(self) -> List[str]:
        """
        List of allowed CORS origins.
        """
        value = self._values.get("cors_allowed_origins", "")
        return value.split(";") if isinstance(value, str) else value

    @property
    def db_file(self) -> str:
        """
        Path to SQLite database file (required).

        Returns the absolute path to the database file, ensuring it resolves correctly
        regardless of the working directory at runtime.
        """
        value = self._values.get("db_file")
        if not value:
            raise ValueError(
                "Critical config missing: 'db_file' must be set in config/environment."
            )

        # Get the app directory path (parent of src)
        app_dir = Path(__file__).parent.parent.parent

        # If value is a relative path, make it absolute from app_dir
        path = Path(value)
        if not path.is_absolute():
            path = app_dir / path

        # Log the absolute path for debugging
        logger.debug("Resolved db_file path: %s", path)

        return str(path)

    @property
    def log_format(self) -> str:
        """
        Logging format.
        """
        return self._values.get(
            "log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    @property
    def log_file(self) -> str:
        """
        Path to log file.
        """
        return self._values.get("log_file", "logs/app.log")

    @property
    def use_mock_hardware(self) -> bool:
        """
        Whether to use mock hardware.
        """
        return self._values.get("use_mock_hardware", False)

    @property
    def app_module(self) -> str:
        """
        ASGI app module for Uvicorn.
        """
        return self._values.get("app_module", "app.main:app_sio")

    @property
    def uvicorn_reload(self) -> bool:
        """
        Whether to enable Uvicorn reload.
        """
        return self._values.get("uvicorn_reload", False)

    # mDNS/zeroconf properties
    @property
    def mdns_service_type(self) -> str:
        """
        Service type for mDNS/zeroconf (e.g. _http._tcp.local.).

        Returns the service type string.
        """
        return self._values.get("mdns_service_type", "_http._tcp.local.")

    @property
    def mdns_service_name(self) -> str:
        """
        Service name for mDNS/zeroconf.

        If not set in config/env, generates a unique name using the system hostname.
        Example: MusicBox-<hostname>._http._tcp.local
        """
        value = self._values.get("mdns_service_name")
        if value:
            return value
        import socket

        hostname = socket.gethostname()
        return f"MusicBox-{hostname}._http._tcp.local"

    @property
    def mdns_service_hostname(self) -> str:
        """
        Get the hostname property for mDNS/zeroconf service.

        Example: <hostname>.local. If not set in config/env, generates <hostname>.local.
        using the system hostname.
        """
        value = self._values.get("mdns_service_hostname")
        if value:
            return value
        import socket

        hostname = socket.gethostname()
        return f"{hostname}.local."

    @property
    def mdns_service_path(self) -> str:
        """
        Path property for mDNS/zeroconf service (e.g. /api).
        """
        return self._values.get("mdns_service_path", "/api")

    @property
    def mdns_service_version(self) -> str:
        """
        Version property for mDNS/zeroconf service (e.g. 1.0).
        """
        return self._values.get("mdns_service_version", "1.0")

    @property
    def mdns_service_friendly_name(self) -> str:
        """
        Human-friendly name for mDNS/zeroconf service.

        The name is used to identify the service in a user-friendly way.
        """
        return self._values.get("mdns_service_friendly_name", "The Open Music Box")

    # Feature flags for paginated playlists optimization
    # Clean architecture - paginated index removed for simplicity

    @property
    def FEATURE_LEGACY_PLAYLISTS_SNAPSHOT(self) -> bool:
        """
        Whether to emit legacy full playlists snapshots over Socket.IO.

        When True, continues to emit state:playlists with full playlist data.
        When False, only emits state:playlists_index_update for optimization.
        """
        return self._values.get("FEATURE_LEGACY_PLAYLISTS_SNAPSHOT", False)

    # === Monitoring Configuration ===

    @property
    def enable_event_monitoring(self) -> bool:
        """
        Whether to enable detailed event monitoring (debug only).

        This setting is automatically disabled if debug mode is off.
        """
        if not self.debug:
            return False
        return self._values.get("enable_event_monitoring", True)

    @property
    def enable_performance_monitoring(self) -> bool:
        """
        Whether to enable performance monitoring.

        This setting is automatically disabled if debug mode is off.
        """
        if not self.debug:
            return False
        return self._values.get("enable_performance_monitoring", True)

    @property
    def monitoring_trace_history_size(self) -> int:
        """
        Maximum events to keep in trace history.
        """
        return self._values.get("monitoring_trace_history_size", 1000)

    @property
    def monitoring_file_logging(self) -> bool:
        """
        Whether to enable monitoring-specific file logging.
        """
        return self._values.get("monitoring_file_logging", False)

    def _load_subconfig_overrides(self) -> None:
        """
        Load environment overrides for sub-configurations.
        """
        # Audio config overrides
        if "AUDIO_DEFAULT_VOLUME" in os.environ:
            self.audio.default_volume = int(os.environ["AUDIO_DEFAULT_VOLUME"])
        if "AUDIO_VOLUME_STEP" in os.environ:
            self.audio.volume_step = int(os.environ["AUDIO_VOLUME_STEP"])

        # Hardware config overrides
        if "USE_MOCK_HARDWARE" in os.environ:
            self.hardware.mock_hardware = os.environ["USE_MOCK_HARDWARE"].lower() in (
                "true",
                "1",
                "yes",
            )
        if "GPIO_NEXT_BUTTON" in os.environ:
            self.hardware.gpio_next_track_button = int(os.environ["GPIO_NEXT_BUTTON"])
        if "GPIO_PREV_BUTTON" in os.environ:
            self.hardware.gpio_previous_track_button = int(os.environ["GPIO_PREV_BUTTON"])
        if "GPIO_VOLUME_CLK" in os.environ:
            self.hardware.gpio_volume_encoder_clk = int(os.environ["GPIO_VOLUME_CLK"])
        if "GPIO_VOLUME_DT" in os.environ:
            self.hardware.gpio_volume_encoder_dt = int(os.environ["GPIO_VOLUME_DT"])
        if "GPIO_VOLUME_SW" in os.environ:
            self.hardware.gpio_volume_encoder_sw = int(os.environ["GPIO_VOLUME_SW"])

        # NFC config overrides
        if "NFC_AUTO_PAUSE" in os.environ:
            self.nfc.auto_pause_enabled = os.environ["NFC_AUTO_PAUSE"].lower() in (
                "true",
                "1",
                "yes",
            )
        if "NFC_AUTO_RESUME" in os.environ:
            self.nfc.auto_resume_enabled = os.environ["NFC_AUTO_RESUME"].lower() in (
                "true",
                "1",
                "yes",
            )

    def _validate_configs(self) -> None:
        """
        Validate all sub-configurations.
        """
        try:
            self.audio.validate()
            self.hardware.validate()
            self.nfc.validate()
        except ValueError as e:
            logger.error("Configuration validation failed: %s", e)
            raise


# Note: AppConfig should be retrieved from DI container
# Use: container.get("config") or get_config()
# Legacy global instance kept for backward compatibility during transition
import warnings
warnings.warn(
    "Global 'config' instance is deprecated. Use dependency injection instead: "
    "container.get('config') or get_config(). "
    "This global will be removed in v2.0 (Q2 2026)",
    DeprecationWarning,
    stacklevel=2
)
config = AppConfig()
