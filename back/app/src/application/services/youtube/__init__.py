# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""YouTube services module initialization.

Provides YouTube-related functionality including video downloading with yt-dlp
and high-level service orchestration. Exposes both the low-level downloader
and the high-level service interface for YouTube integration.
"""

from app.src.infrastructure.youtube.youtube_downloader import YouTubeDownloader
from .youtube_application_service import YouTubeApplicationService

# Backwards compatibility alias
YouTubeService = YouTubeApplicationService

__all__ = ["YouTubeApplicationService", "YouTubeDownloader", "YouTubeService"]
