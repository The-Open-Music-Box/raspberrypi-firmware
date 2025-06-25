# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.
"""Configuration factory for TheOpenMusicBox application.

Provides different configuration types for different environments.
"""

import logging
import os
from enum import Enum, auto
from pathlib import Path

from app.src.config.app_config import AppConfig

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """Configuration types for different environments."""

    DEVELOPMENT = auto()
    PRODUCTION = auto()
    TEST = auto()


class ConfigFactory:
    """Factory class to create appropriate configuration instances.

    This class creates configuration instances based on the environment
    type. It sets appropriate environment variables before initializing
    the configuration.
    """

    @staticmethod
    def create_config(config_type: ConfigType) -> AppConfig:
        """Create a configuration instance for the specified environment.

        Args:
            config_type: The type of configuration to create

        Returns:
            An AppConfig instance configured for the specified environment
        """
        # Set environment variables based on config type
        if config_type == ConfigType.DEVELOPMENT:
            os.environ["DEBUG"] = "True"
            os.environ["USE_MOCK_HARDWARE"] = "True"
            os.environ["USE_RELOADER"] = "True"
            os.environ["UVICORN_RELOAD"] = "True"

        elif config_type == ConfigType.PRODUCTION:
            os.environ["DEBUG"] = "False"
            os.environ["USE_MOCK_HARDWARE"] = "False"
            os.environ["USE_RELOADER"] = "False"
            os.environ["UVICORN_RELOAD"] = "False"

        elif config_type == ConfigType.TEST:
            os.environ["DEBUG"] = "True"
            os.environ["USE_MOCK_HARDWARE"] = "True"
            os.environ["TESTING"] = "True"
            # Use in-memory database for tests
            os.environ["DB_FILE"] = ":memory:"
            # Use temporary upload folder for tests
            test_upload_dir = (
                Path(__file__).parent.parent.parent.parent / "tests" / "uploads"
            )
            os.environ["UPLOAD_FOLDER"] = str(test_upload_dir)

        # Create and return the configuration instance
        from app.src.config.app_config import config

        logger.info(f"Created {config_type.name} configuration")
        return config
