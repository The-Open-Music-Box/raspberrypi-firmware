# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Configuration package for TheOpenMusicBox application.

Provides a unified configuration system with environment variable support.
"""

from app.src.config.app_config import AppConfig, config

# Export public symbols
__all__ = ["AppConfig", "config", "Config"]

# Backward compatibility alias
Config = AppConfig
