# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Playlist service for data domain."""

import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict
import logging

from app.src.domain.decorators.error_handler import handle_domain_errors
from app.src.domain.data.models.playlist import Playlist

logger = logging.getLogger(__name__)


class PlaylistService:
    """Service for managing playlist data operations."""

    def __init__(
        self,
        playlist_repository: Any,
        track_repository: Any
    ):
        """Initialize the playlist service.

        Args:
            playlist_repository: Repository for playlist operations
            track_repository: Repository for track operations
        """
        self._playlist_repo = playlist_repository
        self._track_repo = track_repository
        logger.info("✅ PlaylistService initialized in data domain")

    @handle_domain_errors(operation_name="get_playlists")
    async def get_playlists(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Get paginated playlists.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dictionary with playlists and pagination info
        """
        skip = (page - 1) * page_size

        # Get playlists and total count
        playlist_entities = await self._playlist_repo.find_all(offset=skip, limit=page_size)
        total = await self._playlist_repo.count()

        # Convert Playlist entities to dicts
        playlists = []
        for playlist_entity in playlist_entities:
            if playlist_entity is None:
                continue
            playlist_dict = asdict(playlist_entity)
            # Add track count for each playlist
            playlist_dict['track_count'] = len(playlist_entity.tracks)
            # Ensure title field exists (for API compatibility)
            if 'title' not in playlist_dict and 'name' in playlist_dict:
                playlist_dict['title'] = playlist_dict['name']
            playlists.append(playlist_dict)

        return {
            'playlists': playlists,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }

    @handle_domain_errors(operation_name="get_playlist")
    async def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a single playlist with its tracks.

        Args:
            playlist_id: The playlist ID

        Returns:
            Playlist data with tracks or None
        """
        playlist_entity = await self._playlist_repo.find_by_id(playlist_id)
        if playlist_entity is None:
            return None

        # Convert entity to dict
        playlist_dict = asdict(playlist_entity)
        # Add track count
        playlist_dict['track_count'] = len(playlist_entity.tracks)
        # Ensure title field exists (for API compatibility)
        if 'title' not in playlist_dict and 'name' in playlist_dict:
            playlist_dict['title'] = playlist_dict['name']

        return playlist_dict

    @handle_domain_errors(operation_name="create_playlist")
    async def create_playlist(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new playlist.

        Args:
            name: Playlist name
            description: Optional description

        Returns:
            Created playlist data
        """
        playlist_id = str(uuid.uuid4())
        # Create Playlist entity
        playlist_entity = Playlist(
            id=playlist_id,
            title=name,  # Map name parameter to title field (contract compliance)
            description=description or '',
            tracks=[],  # New playlists start with no tracks
        )

        await self._playlist_repo.save(playlist_entity)
        logger.info(f"✅ Created playlist: {name} (ID: {playlist_id})")

        # Convert to dict for return
        playlist_dict = asdict(playlist_entity)
        playlist_dict['track_count'] = 0  # New playlists start with no tracks
        # Ensure title field exists (for API compatibility)
        if 'title' not in playlist_dict and 'name' in playlist_dict:
            playlist_dict['title'] = playlist_dict['name']
        return playlist_dict

    @handle_domain_errors(operation_name="update_playlist")
    async def update_playlist(self, playlist_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update playlist metadata and rename filesystem directory if title changed.

        Args:
            playlist_id: The playlist ID
            updates: Dictionary of updates

        Returns:
            Updated playlist data
        """
        # Check if playlist exists
        playlist_entity = await self._playlist_repo.find_by_id(playlist_id)
        if playlist_entity is None:
            raise ValueError(f"Playlist {playlist_id} not found")

        # Track if title is being changed (for directory rename)
        old_title = playlist_entity.title
        old_path = playlist_entity.path
        title_changed = False

        # Update the playlist entity with new values
        for key, value in updates.items():
            if key == 'title' and value != old_title:
                title_changed = True
            if hasattr(playlist_entity, key):
                setattr(playlist_entity, key, value)

        updated_entity = await self._playlist_repo.update(playlist_entity)
        if updated_entity is None:
            raise RuntimeError(f"Failed to update playlist {playlist_id}")

        # Rename filesystem directory if title changed
        if title_changed and old_title:
            await self._rename_playlist_folder(playlist_entity, old_title, old_path)

        logger.info(f"✅ Updated playlist {playlist_id}")
        return await self.get_playlist(playlist_id)

    async def _rename_playlist_folder(self, playlist: Playlist, old_title: str, old_path: Optional[str]) -> None:
        """Rename the filesystem directory when playlist title changes.

        Args:
            playlist: Updated playlist entity with new title
            old_title: Previous playlist title
            old_path: Previous playlist path
        """
        try:
            from app.src.config import config as app_config
            from pathlib import Path
            from app.src.utils.path_utils import normalize_folder_name
            import shutil

            upload_folder = Path(app_config.upload_folder)
            new_title = playlist.title

            logger.info(f"📝 Renaming playlist folder: '{old_title}' -> '{new_title}'")

            # Determine old folder path
            old_folder = None
            if old_path:
                old_folder = upload_folder / old_path
            else:
                # Try to find folder by old normalized title
                old_normalized = normalize_folder_name(old_title)
                old_folder_candidate = upload_folder / old_normalized
                if old_folder_candidate.exists():
                    old_folder = old_folder_candidate
                else:
                    # Try original title
                    old_folder_candidate = upload_folder / old_title
                    if old_folder_candidate.exists():
                        old_folder = old_folder_candidate

            if not old_folder or not old_folder.exists():
                logger.warning(f"📁 Old folder not found, skipping rename: {old_folder}")
                return

            # Determine new folder path
            new_normalized = normalize_folder_name(new_title)
            new_folder = upload_folder / new_normalized

            # Rename the directory
            if old_folder != new_folder:
                if new_folder.exists():
                    logger.warning(f"⚠️ Target folder already exists: {new_folder}")
                    return

                shutil.move(str(old_folder), str(new_folder))
                logger.info(f"✅ Renamed playlist folder: {old_folder} -> {new_folder}")

                # Update track file_paths in database
                await self._update_track_file_paths(playlist.id, old_folder, new_folder)
            else:
                logger.debug(f"📁 Folder names are the same, no rename needed")

        except Exception as e:
            logger.warning(f"⚠️ Failed to rename folder for playlist {playlist.title}: {e}")
            # Don't fail the update operation if folder rename fails

    async def _update_track_file_paths(self, playlist_id: str, old_folder: Path, new_folder: Path) -> None:
        """Update track file_paths after playlist folder rename.

        Args:
            playlist_id: Playlist identifier
            old_folder: Old folder path
            new_folder: New folder path
        """
        try:
            tracks = await self._track_repo.get_by_playlist(playlist_id)
            old_folder_str = str(old_folder)

            for track in tracks:
                track_dict = asdict(track) if not isinstance(track, dict) else track
                old_file_path = track_dict.get('file_path', '')

                if old_file_path and old_folder_str in old_file_path:
                    new_file_path = old_file_path.replace(old_folder_str, str(new_folder))
                    track_id = track_dict.get('id')

                    if track_id:
                        await self._track_repo.update(track_id, {'file_path': new_file_path})
                        logger.debug(f"Updated track file_path: {old_file_path} -> {new_file_path}")

            logger.info(f"✅ Updated file paths for {len(tracks)} tracks in playlist {playlist_id}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to update track file paths: {e}")

    @handle_domain_errors(operation_name="delete_playlist")
    async def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist, all its tracks, and filesystem directory.

        Args:
            playlist_id: The playlist ID

        Returns:
            True if successful
        """
        # Get playlist info before deletion (for filesystem cleanup)
        playlist = await self._playlist_repo.find_by_id(playlist_id)

        # Delete all tracks first
        deleted_tracks = await self._track_repo.delete_tracks_by_playlist(playlist_id)
        logger.info(f"Deleted tracks from playlist {playlist_id}")

        # Delete the playlist from database
        success = await self._playlist_repo.delete(playlist_id)
        if success:
            logger.info(f"✅ Deleted playlist {playlist_id} from database")

            # Clean up filesystem directory
            if playlist:
                await self._cleanup_playlist_folder(playlist)
        else:
            logger.warning(f"Failed to delete playlist {playlist_id}")

        return success

    async def _cleanup_playlist_folder(self, playlist: Playlist) -> None:
        """Clean up the filesystem directory for a deleted playlist.

        Args:
            playlist: Playlist domain entity
        """
        try:
            from app.src.config import config as app_config
            from pathlib import Path
            from app.src.utils.path_utils import normalize_folder_name
            import shutil

            upload_folder = Path(app_config.upload_folder)
            playlist_title = playlist.title
            playlist_path = playlist.path
            playlist_id = playlist.id

            logger.info(f"🧹 Starting folder cleanup for playlist: {playlist_title}")

            # List of possible folder names to check
            possible_folders = []

            # 1. Use the stored path (new format)
            if playlist_path:
                folder_path = upload_folder / playlist_path
                possible_folders.append(folder_path)

            # 2. Try normalized path based on title
            if playlist_title:
                normalized_path = normalize_folder_name(playlist_title)
                folder_path = upload_folder / normalized_path
                possible_folders.append(folder_path)

                # 3. Try original title as folder name
                folder_path = upload_folder / playlist_title
                possible_folders.append(folder_path)

            # 4. Fallback: try playlist ID as folder name
            if playlist_id:
                folder_path = upload_folder / playlist_id
                possible_folders.append(folder_path)

            # Try to remove any of the possible folders
            removed_folders = []
            for folder_path in possible_folders:
                if folder_path.exists() and folder_path.is_dir():
                    logger.info(f"🗂️ Removing folder: {folder_path}")
                    shutil.rmtree(folder_path)
                    removed_folders.append(str(folder_path))
                    logger.info(f"✅ Removed playlist folder: {folder_path}")

            if not removed_folders:
                logger.warning(f"📁 No folder found to clean up for playlist: {playlist_title}")
            elif len(removed_folders) > 1:
                logger.info(f"🗂️ Removed multiple folders: {removed_folders}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to clean up folder for playlist {playlist.title}: {e}")
            # Don't fail the delete operation if folder cleanup fails

    @handle_domain_errors(operation_name="associate_nfc_tag")
    async def associate_nfc_tag(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Associate an NFC tag with a playlist.

        Args:
            playlist_id: The playlist ID
            nfc_tag_id: The NFC tag ID

        Returns:
            True if successful
        """
        updates = {
            'nfc_tag_id': nfc_tag_id,
            'updated_at': datetime.utcnow().isoformat()
        }

        success = await self._playlist_repo.update(playlist_id, updates)
        if success:
            logger.info(f"✅ Associated NFC tag {nfc_tag_id} with playlist {playlist_id}")

        return success

    @handle_domain_errors(operation_name="get_playlist_by_nfc")
    async def get_playlist_by_nfc(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist associated with an NFC tag.

        Args:
            nfc_tag_id: The NFC tag ID

        Returns:
            Playlist data or None
        """
        # Use find_by_nfc_tag to match repository interface
        playlist_entity = await self._playlist_repo.find_by_nfc_tag(nfc_tag_id)
        if playlist_entity is None:
            return None

        # Convert entity to dict (tracks are already included in entity)
        from dataclasses import asdict
        playlist_dict = asdict(playlist_entity)
        playlist_dict['track_count'] = len(playlist_entity.tracks)
        # Ensure title field exists (for API compatibility)
        if 'title' not in playlist_dict and 'name' in playlist_dict:
            playlist_dict['title'] = playlist_dict['name']

        return playlist_dict

    @handle_domain_errors(operation_name="sync_with_filesystem")
    async def sync_with_filesystem(self, upload_folder: str) -> Dict[str, Any]:
        """Synchronize playlists with filesystem.

        Args:
            upload_folder: Path to the upload folder

        Returns:
            Synchronization statistics
        """
        stats = {
            'playlists_scanned': 0,
            'playlists_added': 0,
            'playlists_updated': 0,
            'tracks_added': 0,
            'tracks_removed': 0
        }

        upload_path = Path(upload_folder)
        if not upload_path.exists():
            logger.warning(f"Upload folder does not exist: {upload_folder}")
            return stats

        # Scan all directories in upload folder
        for playlist_dir in upload_path.iterdir():
            if not playlist_dir.is_dir():
                continue

            stats['playlists_scanned'] += 1
            playlist_name = playlist_dir.name

            # Check if playlist already exists
            existing_playlists = await self._playlist_repo.get_all()
            existing = next(
                (p for p in existing_playlists if p['title'] == playlist_name),
                None
            )

            if existing:
                # Update tracks for existing playlist
                await self._sync_playlist_tracks(existing['id'], playlist_dir, stats)
            else:
                # Create new playlist
                playlist = await self.create_playlist(
                    name=playlist_name,
                    description=f"Auto-imported from {playlist_dir.name}"
                )
                stats['playlists_added'] += 1
                await self._sync_playlist_tracks(playlist['id'], playlist_dir, stats)

        logger.info(f"✅ Filesystem sync completed: {stats}")
        return stats

    async def _sync_playlist_tracks(self, playlist_id: str, playlist_dir: Path, stats: Dict[str, Any]):
        """Synchronize tracks for a playlist.

        Args:
            playlist_id: The playlist ID
            playlist_dir: Directory containing audio files
            stats: Statistics dictionary to update
        """
        # Get audio files
        audio_extensions = {'.mp3', '.flac', '.wav', '.m4a', '.ogg'}
        audio_files = sorted([
            f for f in playlist_dir.iterdir()
            if f.is_file() and f.suffix.lower() in audio_extensions
        ])

        # Get existing tracks
        existing_tracks = await self._track_repo.get_by_playlist(playlist_id)
        existing_files = {t['filename'] for t in existing_tracks if t.get('filename')}

        # Add new tracks
        for idx, audio_file in enumerate(audio_files, 1):
            if audio_file.name not in existing_files:
                track_data = {
                    'id': str(uuid.uuid4()),
                    'playlist_id': playlist_id,
                    'track_number': idx,
                    'title': audio_file.stem,
                    'filename': audio_file.name,
                    'file_path': str(audio_file),
                    'created_at': datetime.utcnow().isoformat()
                }
                await self._track_repo.add_to_playlist(playlist_id, track_data)
                stats['tracks_added'] += 1

        # Remove tracks that no longer exist
        current_files = {f.name for f in audio_files}
        for track in existing_tracks:
            if track.get('filename') and track['filename'] not in current_files:
                await self._track_repo.delete(track['id'])
                stats['tracks_removed'] += 1
