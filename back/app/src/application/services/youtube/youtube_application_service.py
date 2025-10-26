# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""YouTube service for handling video downloads and playlist creation.

Provides high-level service interface for YouTube video downloads, chapter
processing, playlist database integration, and real-time progress notifications
via Socket.IO. Coordinates between downloader and playlist services.
"""

from pathlib import Path
from typing import Dict
from uuid import uuid4
import logging

from app.src.services.notification_service import DownloadNotifier
from app.src.infrastructure.youtube.youtube_downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


class YouTubeApplicationService:
    """Service for handling YouTube download requests and playlist creation."""

    def __init__(self, socketio=None, config=None):
        self.socketio = socketio
        self.config = config
        self.data_application_service = None  # Will be set on first use

    def _get_data_application_service(self):
        """Get data application service with deferred import to avoid circular dependency."""
        if self.data_application_service is None:
            from app.src.dependencies import get_data_application_service
            self.data_application_service = get_data_application_service()
        return self.data_application_service

    async def process_download(self, url: str) -> Dict:
        """Process a YouTube download request asynchronously.

        This method handles the entire download workflow:
        1. Download the video/audio
        2. Process chapters if available
        3. Create a playlist in the database
        4. Send notifications about the progress
        """
        download_id = str(uuid4())
        notifier = DownloadNotifier(self.socketio, download_id)

        try:
            # Initial notification
            await notifier.notify(
                status="pending", message="Download request received, preparing..."
            )

            # Create downloader with async progress callback
            # The callback will pass through all status updates from the downloader
            downloader = YouTubeDownloader(
                upload_folder=self.config.upload_folder,
                progress_callback=lambda p_data: notifier.notify(**p_data),
            )

            # Download the video
            # This will send progress notifications via the callback
            result = await downloader.download(url)

            # Notify that we're saving to the database
            await notifier.notify(
                status="saving_playlist",
                message="Download complete, saving playlist to database...",
            )

            # Process the result
            base_folder = Path(self.config.upload_folder).name
            relative_path = Path(base_folder) / result["folder"]

            # Create playlist using new architecture
            data_service = self._get_data_application_service()
            
            # Create playlist first
            playlist_result = await data_service.create_playlist_use_case(
                name=result["title"],
                description=f"YouTube download from {url}"
            )
            playlist_id = playlist_result.get("id")
            
            # Add tracks/chapters to the playlist
            tracks = result.get("chapters", [])
            for track_data in tracks:
                # Adapt track data to expected format
                track_info = {
                    "title": track_data.get("title", "Unknown Track"),
                    "filename": track_data.get("filename"),
                    "start_time": track_data.get("start_time", 0),
                    "end_time": track_data.get("end_time", 0),
                    "folder": str(relative_path)
                }
                await data_service.add_track_use_case(playlist_id, track_info)

            # Send completion notification
            await notifier.notify(
                status="complete",
                playlist_id=playlist_id,
                message=f'Playlist "{result["title"]}" created successfully with {len(tracks)} tracks!',
            )

            # Emit a dedicated event for playlist updates to help frontend refresh its
            # data
            if self.socketio:
                await self.socketio.emit(
                    "playlists_updated",
                    {
                        "action": "created",
                        "playlist_id": playlist_id,
                        "playlist_title": result["title"],
                        "tracks_count": len(tracks),
                    },
                )

            return {"status": "success", "playlist_id": playlist_id, "data": result}

        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            await notifier.notify(
                status="error",
                error=str(e),
                message=f"An error occurred during download: {str(e)}",
            )
            raise

    async def search_videos(self, query: str, max_results: int = 10) -> Dict:
        """Search for YouTube videos.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing search results
        """
        try:
            logger.info(f"YouTubeService: Searching for videos with query: {query}")

            # For now, return mock search results
            # In a real implementation, this would use the YouTube API
            mock_results = {
                "query": query,
                "results": [
                    {
                        "id": "dQw4w9WgXcQ",
                        "title": f"Mock result for '{query}' - Video 1",
                        "description": "This is a mock search result",
                        "duration": "3:35",
                        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg"
                    },
                    {
                        "id": "9bZkp7q19f0",
                        "title": f"Mock result for '{query}' - Video 2",
                        "description": "Another mock search result",
                        "duration": "4:12",
                        "thumbnail": "https://i.ytimg.com/vi/9bZkp7q19f0/default.jpg"
                    }
                ][:max_results],
                "total_results": min(max_results, 2)
            }

            logger.info(f"YouTubeService: Found {len(mock_results['results'])} results")
            return mock_results

        except Exception as e:
            logger.error(f"YouTubeService: Search failed: {str(e)}")
            raise

    async def get_task_status(self, task_id: str) -> Dict:
        """Get the status of a YouTube download task.

        Args:
            task_id: The task ID to check

        Returns:
            Dictionary containing task status or None if not found
        """
        try:
            logger.info(f"YouTubeService: Checking status for task: {task_id}")

            # For now, return mock task status
            # In a real implementation, this would check a task queue/database
            mock_status = {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "message": "Download completed successfully",
                "created_at": "2025-09-28T23:00:00Z",
                "updated_at": "2025-09-28T23:00:30Z"
            }

            logger.info(f"YouTubeService: Task {task_id} status: {mock_status['status']}")
            return mock_status

        except Exception as e:
            logger.error(f"YouTubeService: Status check failed: {str(e)}")
            raise
