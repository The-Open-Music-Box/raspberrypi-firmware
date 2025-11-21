# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Filesystem synchronization service for playlist management.

This service handles synchronization between the filesystem and playlist database,
including scanning for new playlists, updating existing ones, and managing
audio file metadata extraction.
"""

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime, timezone

# Direct imports following DDD principles
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.services.upload_service import UploadService

logger = logging.getLogger(__name__)


class FilesystemSyncService:
    """Service for synchronizing playlists with the filesystem.

    Handles scanning directories for audio files, creating playlists from folders,
    and keeping the database synchronized with filesystem changes.
    """

    # Supported audio file extensions
    SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac"}

    # Synchronization timeouts (in seconds)
    SYNC_TOTAL_TIMEOUT = 120.0  # 2 minutes for total sync
    SYNC_FOLDER_TIMEOUT = 30.0  # 30 seconds for folder scanning
    SYNC_OPERATION_TIMEOUT = 10.0  # 10 seconds per operation

    def __init__(self, config_obj=None):
        """Initialize the FilesystemSyncService.

        Args:
            config_obj: Optional configuration object. If not provided, uses global config.
        """
        from app.src.config import config as global_config

        self.config = config_obj or global_config
        # Pure DDD - get repository via dependency injection
        from app.src.dependencies import get_playlist_repository_adapter
        self.repository = get_playlist_repository_adapter()
        self.upload_folder = Path(self.config.upload_folder)
        self._sync_lock = threading.RLock()

    @handle_service_errors("filesystem_sync")
    async def create_playlist_from_folder(
        self, folder_path: Path, title: Optional[str] = None
    ) -> Optional[str]:
        """Create a playlist from a folder of audio files.

        This scans the specified folder for supported audio files and creates a new
        playlist entry in the database, with each file as a track. The playlist's
        relative path is determined with respect to the upload folder.

        Args:
            folder_path: Path to the folder
            title: Optional title for the playlist (default: folder name)

        Returns:
            ID of the created playlist or None if an error occurred
        """
        # Check if the folder exists and is a directory
        if not folder_path.exists() or not folder_path.is_dir():
            logger.error(f"Folder does not exist: {folder_path}")
            return None
        # Retrieve audio files in the folder
        audio_files = [
            f
            for f in folder_path.iterdir()
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS
        ]
        # Check if there are any audio files
        if not audio_files:
            logger.warning(f"No audio files found in folder: {folder_path}")
            return None
        # Determine the relative path with respect to the parent of the uploads folder
        rel_path = folder_path.relative_to(self.upload_folder.parent)
        # Initialize the playlist data
        playlist_data = {
            "id": str(uuid4()),
            "type": "playlist",
            "title": title or folder_path.name,
            "path": str(rel_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tracks": [],
        }
        # Use UploadService to extract metadata for each audio file
        upload_service = UploadService(self.config)
        for i, file_path in enumerate(sorted(audio_files), 1):
            metadata = upload_service.extract_metadata(file_path)
            # Convert duration from seconds to milliseconds for consistency
            duration_seconds = metadata.get("duration", 0)
            duration_ms = int(duration_seconds * 1000) if duration_seconds else 0
            track = {
                "track_number": i,
                "title": metadata.get("title", file_path.stem),
                "filename": file_path.name,
                "duration": duration_ms,  # Now in milliseconds like other services
                "artist": metadata.get("artist", "Unknown"),
                "album": metadata.get("album", "Unknown"),
                "play_counter": 0,
            }
            playlist_data["tracks"].append(track)
        # Create the playlist in the repository
        return await self.repository.create_playlist(playlist_data)

    @handle_service_errors("filesystem_sync")
    async def update_playlist_tracks(
        self, playlist_id: str, folder_path: Path
    ) -> Tuple[bool, Dict[str, int]]:
        """Update the tracks of a playlist from the contents of a folder.

        This method compares the current tracks in the playlist with the audio files
        present in the specified folder. It adds new tracks for new files, removes
        tracks for missing files, and keeps existing tracks that are still present.

        Args:
            playlist_id: Playlist ID
            folder_path: Path to the folder

        Returns:
            Tuple (success, statistics)
        """
        stats = {"added": 0, "removed": 0}

        # Retrieve the existing playlist
        playlist = await self.repository.get_playlist_by_id(playlist_id)
        if not playlist:
            logger.warning(f"Playlist not found: {playlist_id}")
            return False, stats
        # Retrieve audio files in the folder
        audio_files = [
            f
            for f in folder_path.iterdir()
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS
        ]
        # Create dictionaries for comparison
        existing_tracks = {t["filename"]: t for t in playlist.get("tracks", [])}
        disk_files_map = {f.name: f for f in audio_files}
        # Identify modifications
        to_remove = set(existing_tracks.keys()) - set(disk_files_map.keys())
        to_add = set(disk_files_map.keys()) - set(existing_tracks.keys())
        # Prepare new tracks
        new_tracks = []
        track_number = 1
        # Keep existing tracks that are still present
        for filename, track in existing_tracks.items():
            if filename not in to_remove:
                track_copy = dict(track)
                track_copy["track_number"] = track_number
                new_tracks.append(track_copy)
                track_number += 1
        # Add new tracks
        for filename in sorted(to_add):
            file_path = disk_files_map[filename]
            new_track = {
                "track_number": track_number,
                "title": file_path.stem,
                "filename": filename,
                "duration": "",
                "artist": "Unknown",
                "album": "Unknown",
                "play_counter": 0,
            }
            new_tracks.append(new_track)
            track_number += 1
        # Update the playlist
        if await self.repository.replace_tracks(playlist_id, new_tracks):
            stats["added"] = len(to_add)
            stats["removed"] = len(to_remove)
            logger.info(
                f"Updated playlist {playlist_id}: added {stats['added']}, removed {stats['removed']} tracks"
            )
            return True, stats
        return False, stats

    @handle_service_errors("filesystem_sync")
    async def sync_with_filesystem(self) -> Dict[str, int]:
        """Synchronize playlists in the database with the filesystem.

        Returns:
            Synchronization statistics
        """
        with self._sync_lock:  # Prevent concurrent synchronizations
            start_time = time.time()
            stats = {
                "playlists_scanned": 0,
                "playlists_added": 0,
                "playlists_updated": 0,
                "tracks_added": 0,
                "tracks_removed": 0,
            }

            logger.info(
                f"Starting playlist synchronization with {self.upload_folder}"
            )
            # 1. Check that the uploads folder exists
            if not self.upload_folder.exists():
                self.upload_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created upload folder: {self.upload_folder}")
            # 2. Retrieve existing playlists
            db_playlists = await self.repository.get_all_playlists()
            db_playlists_by_path = {p.get("path", ""): p for p in db_playlists}

            # Also create a mapping by title/folder name for better duplicate detection
            # This handles cases where the playlist title matches the folder name
            db_playlists_by_title = {}
            for p in db_playlists:
                title = p.get("title", "")
                if title:
                    # Store lowercase to handle case-insensitive matching
                    db_playlists_by_title[title.lower()] = p
                    # Also try to match by the last part of the path (folder name)
                    path_parts = p.get("path", "").split("/")
                    if path_parts:
                        folder_name = path_parts[-1].lower()
                        if folder_name and folder_name not in db_playlists_by_title:
                            db_playlists_by_title[folder_name] = p
            # 3. Scan the filesystem with timeout
            disk_playlists = self._scan_filesystem_with_timeout()
            # 4. Iterate through existing playlists to update them
            await self._update_existing_playlists(db_playlists, disk_playlists, stats)
            # 5. Add new playlists
            if time.time() - start_time < self.SYNC_TOTAL_TIMEOUT:
                await self._add_new_playlists(
                    disk_playlists, db_playlists_by_path, db_playlists_by_title, stats
                )
            else:
                logger.warning("Skipping new playlists due to timeout")
            elapsed = time.time() - start_time
            logger.info(f"Playlist sync completed in {elapsed:.2f}s",
                extra=stats,
            )
            return stats

    @handle_service_errors("filesystem_sync")
    def _scan_filesystem_with_timeout(self) -> Dict[str, List[Path]]:
        """Scan the filesystem with protection against timeouts.

        Returns:
            Dictionary mapping playlist paths to audio files
        """
        result = {}
        scan_start = time.time()

        for item in self.upload_folder.iterdir():
            # Check global timeout
            if time.time() - scan_start > self.SYNC_FOLDER_TIMEOUT:
                logger.warning("Folder scan timeout, processing items scanned so far",
                )
                break
            if item.is_dir():
                # Relative path with respect to the parent of the uploads folder
                rel_path = str(item.relative_to(self.upload_folder.parent))
                audio_files = []
                folder_scan_start = time.time()
                for f in item.iterdir():
                    # Timeout per folder
                    if time.time() - folder_scan_start > self.SYNC_OPERATION_TIMEOUT:
                        logger.warning(f"Partial scan of {rel_path} due to timeout",
                        )
                        break
                    if f.is_file() and f.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS:
                        audio_files.append(f)

                # Add to result if audio files were found
                if audio_files:
                    result[rel_path] = audio_files
        return result

    @handle_service_errors("filesystem_sync")
    async def _update_existing_playlists(
        self,
        db_playlists: List[Dict[str, Any]],
        disk_playlists: Dict[str, List[Path]],
        stats: Dict[str, int],
    ) -> None:
        """Update existing playlists with files from disk.

        Args:
            db_playlists: List of playlists in the database
            disk_playlists: Dictionary of files found on disk
            stats: Dictionary of statistics to update
        """
        start_time = time.time()

        for db_playlist in db_playlists:
            if time.time() - start_time > self.SYNC_TOTAL_TIMEOUT:
                logger.warning("Update timeout reached, stopping updates")
                break

            stats["playlists_scanned"] += 1
            path = db_playlist.get("path", "")

            # If the folder no longer exists or is empty, no need to update
            if path not in disk_playlists:
                continue

            # Update with the files found
            disk_files = disk_playlists.get(path, [])
            if disk_files:
                success, update_stats = await self.update_playlist_tracks(
                    db_playlist["id"], Path(self.upload_folder.parent / path)
                )
                if success:
                    stats["playlists_updated"] += 1
                    stats["tracks_added"] += update_stats["added"]
                    stats["tracks_removed"] += update_stats["removed"]

    async def _add_new_playlists(
        self,
        disk_playlists: Dict[str, List[Path]],
        db_playlists_by_path: Dict[str, Dict[str, Any]],
        db_playlists_by_title: Dict[str, Dict[str, Any]],
        stats: Dict[str, int],
    ) -> None:
        """Add new playlists found on disk.

        Args:
            disk_playlists: Dictionary of files found on disk
            db_playlists_by_path: Dictionary of existing playlists by path
            db_playlists_by_title: Dictionary of existing playlists by title/folder name
            stats: Dictionary of statistics to update
        """
        start_time = time.time()

        for path, audio_files in disk_playlists.items():
            if time.time() - start_time > self.SYNC_TOTAL_TIMEOUT:
                logger.warning("Add timeout reached, stopping additions")
                break

            # Check if playlist already exists by path or by folder name
            folder_name = Path(path).name.lower()

            # Skip if playlist exists by path
            if path in db_playlists_by_path:
                logger.debug(f"Playlist already exists by path: {path}")
                continue

            # Skip if playlist exists by folder name/title
            if folder_name in db_playlists_by_title:
                existing_playlist = db_playlists_by_title[folder_name]
                logger.info(f"Playlist already exists with name '{folder_name}' (ID: {existing_playlist.get('id')}), skipping duplicate creation",
                )
                continue

            # If the playlist doesn't exist in the database, create it
            if True:  # Keep the same indentation level for the rest of the code
                try:
                    folder_path = Path(self.upload_folder.parent / path)
                    playlist_id = await self.create_playlist_from_folder(folder_path)
                    if playlist_id:
                        stats["playlists_added"] += 1
                        stats["tracks_added"] += len(audio_files)
                        logger.info(f"Created new playlist from folder: {path} (ID: {playlist_id})",
                        )
                except (OSError, IOError, PermissionError, ValueError) as e:
                    logger.error(f"Error creating playlist from folder {path}: {str(e)}",
                    )
