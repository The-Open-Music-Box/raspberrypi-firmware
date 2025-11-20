# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Configuration for the unified monitoring system.

DEPRECATED: MonitoringConfig has been moved to app.src.config.monitoring_config
to comply with Clean Architecture dependency rules (infrastructure should not
import from monitoring layer).

This module re-exports from the new location for backward compatibility.
"""

import warnings

# Warn on import
warnings.warn(
    "Importing from 'app.src.monitoring.config' is deprecated. "
    "Use 'app.src.config.monitoring_config' instead. "
    "This module will be removed in v2.0 (Q2 2026)",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from app.src.config.monitoring_config import (
    MonitoringConfig,
    monitoring_config,
)

__all__ = ["MonitoringConfig", "monitoring_config"]
