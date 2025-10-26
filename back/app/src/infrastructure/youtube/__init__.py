# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""YouTube infrastructure module initialization.

Provides YouTube-related infrastructure services including video downloading
and external API integrations.
"""

from .youtube_downloader import YouTubeDownloader

__all__ = ["YouTubeDownloader"]