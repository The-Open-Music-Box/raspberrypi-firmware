# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Routes module initialization for TheOpenMusicBox backend.

Exposes the main route classes for HTTP endpoints including web routes,
NFC management routes, and YouTube integration routes. Provides a centralized
import point for all route handlers.
"""

from .nfc_unified_routes import UnifiedNFCRoutes as NFCRoutes
from .web_routes import WebRoutes
from .youtube_routes import YouTubeRoutes

__all__ = ["WebRoutes", "NFCRoutes", "YouTubeRoutes"]
