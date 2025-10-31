# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Playlist service for data domain."""

import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import asdict
import logging

from app.src.domain.decorators.error_handler import handle_domain_errors
from app.src.domain.data.models.playlist import Playlist
from app.src.config import config as app_config

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
        """Update playlist metadata.

        With UUID-based folder names, no filesystem operations are needed when title changes.

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

        # Update the playlist entity with new values
        for key, value in updates.items():
            if hasattr(playlist_entity, key):
                setattr(playlist_entity, key, value)

        updated_entity = await self._playlist_repo.update(playlist_entity)
        if updated_entity is None:
            raise RuntimeError(f"Failed to update playlist {playlist_id}")

        logger.info(f"✅ Updated playlist {playlist_id}")
        return await self.get_playlist(playlist_id)


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
            # IMPORTANT: Check 'is not None' explicitly because empty playlists have len() == 0
            # which evaluates to False in boolean context
            if playlist is not None:
                await self._cleanup_playlist_folder(playlist)
            else:
                logger.warning(f"⚠️ Skipping filesystem cleanup - playlist entity not found")
        else:
            logger.warning(f"Failed to delete playlist {playlist_id}")

        return success

    async def _cleanup_playlist_folder(self, playlist: Playlist) -> None:
        """Clean up the filesystem directory for a deleted playlist.

        With UUID-based folder names, cleanup is straightforward - just delete the folder at playlist.path.

        Args:
            playlist: Playlist domain entity
        """
        try:
            if not playlist.path:
                logger.warning(f"📁 No path set for playlist {playlist.title}, skipping cleanup")
                return

            upload_folder = Path(app_config.upload_folder)
            folder_path = upload_folder / playlist.path

            if folder_path.exists() and folder_path.is_dir():
                logger.info(f"🗂️ Removing folder: {folder_path}")
                shutil.rmtree(folder_path)
                logger.info(f"✅ Removed playlist folder: {folder_path}")
            else:
                logger.warning(f"📁 Folder not found: {folder_path}")

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
        """Synchronize playlists with filesystem, migrating old folder names to UUID.

        This method handles both:
        - New UUID-named folders (direct match via path)
        - Legacy title-based folders (migration to UUID)

        Args:
            upload_folder: Path to the upload folder

        Returns:
            Synchronization statistics including folders_migrated count
        """
        stats = {
            'playlists_scanned': 0,
            'playlists_added': 0,
            'playlists_updated': 0,
            'folders_migrated': 0,  # Track folder renames during migration
            'tracks_added': 0,
            'tracks_removed': 0
        }

        upload_path = Path(upload_folder)
        if not upload_path.exists():
            logger.warning(f"Upload folder does not exist: {upload_folder}")
            return stats

        # Get all playlists once for efficiency
        all_playlists = await self._playlist_repo.find_all()

        # Scan all directories in upload folder
        for playlist_dir in upload_path.iterdir():
            if not playlist_dir.is_dir():
                continue

            stats['playlists_scanned'] += 1
            folder_name = playlist_dir.name

            # Strategy 1: Try to find playlist by path (UUID match - for already migrated playlists)
            existing = next((p for p in all_playlists if p.path == folder_name), None)

            # Strategy 2: Try to find by title (for legacy folders needing migration)
            if not existing:
                existing = next((p for p in all_playlists if p.title == folder_name), None)

                if existing:
                    # Migr folder: rename to UUID and update DB
                    logger.info(f"🔄 Migrating legacy folder '{folder_name}' to UUID-based name")
                    new_folder_name = existing.path if existing.path else str(uuid.uuid4())
                    new_folder_path = upload_path / new_folder_name

                    try:
                        playlist_dir.rename(new_folder_path)

                        # Update path in DB if not set
                        if not existing.path:
                            existing.path = new_folder_name
                            await self._playlist_repo.update(existing)

                        # Update track file_paths
                        tracks = await self._track_repo.get_tracks_by_playlist(existing.id)
                        for track in tracks:
                            if track.file_path and str(playlist_dir) in track.file_path:
                                new_file_path = track.file_path.replace(str(playlist_dir), str(new_folder_path))
                                await self._track_repo.update_track(track.id, {'file_path': new_file_path})

                        playlist_dir = new_folder_path  # Use new path for track sync
                        stats['folders_migrated'] += 1
                        logger.info(f"✅ Migrated folder: {folder_name} → {new_folder_name}")
                    except Exception as e:
                        logger.error(f"Failed to migrate folder {folder_name}: {e}")
                        # Continue with old folder if migration fails

            if existing:
                # Update tracks for existing playlist
                await self._sync_playlist_tracks(existing.id, playlist_dir, stats)
                stats['playlists_updated'] += 1
            else:
                # Create new playlist (folder name doesn't match any existing playlist)
                # Use folder name as title if it looks like a title, otherwise generate a title
                if len(folder_name) == 36 and folder_name.count('-') == 4:
                    # Looks like a UUID - generate a better title
                    playlist_title = f"Playlist {folder_name[:8]}"
                else:
                    # Use folder name as title
                    playlist_title = folder_name

                playlist = await self.create_playlist(
                    name=playlist_title,
                    description=f"Auto-imported from filesystem"
                )
                stats['playlists_added'] += 1

                # If folder isn't already UUID, rename it to match the playlist's UUID path
                playlist_entity = await self._playlist_repo.find_by_id(playlist['id'])
                if playlist_entity and playlist_entity.path != folder_name:
                    try:
                        new_folder_path = upload_path / playlist_entity.path
                        playlist_dir.rename(new_folder_path)
                        playlist_dir = new_folder_path
                        logger.info(f"✅ Renamed new playlist folder: {folder_name} → {playlist_entity.path}")
                    except Exception as e:
                        logger.error(f"Failed to rename new playlist folder {folder_name}: {e}")

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
        existing_tracks = await self._track_repo.get_tracks_by_playlist(playlist_id)
        existing_files = {t.filename for t in existing_tracks if t.filename}

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
                await self._track_repo.add_track_to_playlist(playlist_id, track_data)
                stats['tracks_added'] += 1

        # Remove tracks that no longer exist
        current_files = {f.name for f in audio_files}
        for track in existing_tracks:
            if track.filename and track.filename not in current_files:
                await self._track_repo.delete_track(track.id)
                stats['tracks_removed'] += 1

    @handle_domain_errors(operation_name="cleanup_orphaned_folders")
    async def cleanup_orphaned_folders(self, upload_folder: str) -> Dict[str, Any]:
        """Remove folders in upload directory that have no corresponding playlist in database.

        This is the inverse operation of sync_with_filesystem():
        - sync_with_filesystem: uploads → DB (create missing playlists)
        - cleanup_orphaned_folders: DB → uploads (remove orphaned folders)

        Args:
            upload_folder: Path to the upload folder

        Returns:
            Cleanup statistics with folders_scanned, folders_removed, removed_paths
        """
        import shutil

        stats = {
            'folders_scanned': 0,
            'folders_removed': 0,
            'removed_paths': []
        }

        upload_path = Path(upload_folder)
        if not upload_path.exists():
            logger.warning(f"Upload folder does not exist: {upload_folder}")
            return stats

        # Get all playlists from database
        all_playlists = await self._playlist_repo.find_all()

        # Build sets of known paths and titles (case-insensitive)
        db_paths = set()
        db_titles = set()
        for playlist in all_playlists:
            if playlist.path:
                db_paths.add(playlist.path)
            if playlist.title:
                db_titles.add(playlist.title.lower())

        # Scan upload folder for orphaned directories
        for folder in upload_path.iterdir():
            if not folder.is_dir():
                continue

            stats['folders_scanned'] += 1
            folder_name = folder.name

            # Check if folder corresponds to any playlist (by path or title)
            is_in_db = (
                folder_name in db_paths or
                folder_name.lower() in db_titles
            )

            if not is_in_db:
                # Orphaned folder - remove it
                try:
                    shutil.rmtree(folder)
                    stats['folders_removed'] += 1
                    stats['removed_paths'].append(str(folder))
                    logger.info(f"🗑️ Removed orphaned folder: {folder}")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned folder {folder}: {e}")

        logger.info(f"✅ Cleanup completed: {stats}")
        return stats
