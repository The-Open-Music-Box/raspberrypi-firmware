# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Pure DDD Playlist Repository Adapter

Clean adapter for domain layer to access pure DDD repository implementation.
Follows proper dependency injection and pure DDD principles.
"""

from typing import Any, Dict, List, Optional
import logging
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.services.error.unified_error_decorator import handle_repository_errors

logger = logging.getLogger(__name__)

def _handle_repository_errors(component_name: str):
    return handle_repository_errors(component_name)


class PurePlaylistRepositoryAdapter:
    """Pure DDD playlist repository adapter.

    This adapter provides a clean interface for the domain layer to access
    playlist repository operations following pure DDD principles.
    """

    def __init__(self):
        """Initialize pure DDD repository adapter.

        Uses direct container access to avoid circular dependencies.
        """
        self._repository = None  # Will be injected via property
        logger.info("✅ Pure DDD Playlist Repository Adapter initialized")

    @property
    def _repo(self):
        """Lazy-loaded repository instance from container."""
        if self._repository is None:
            # Direct container access to avoid circular dependency
            from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
            self._repository = PureSQLitePlaylistRepository()
            logger.info("✅ Repository directly instantiated to avoid circular dependency")
        return self._repository

    @_handle_repository_errors("playlist_adapter")
    async def create_playlist(self, playlist_data: Dict[str, Any]) -> str:
        """Create playlist using pure DDD principles."""
        # Create tracks first from data
        tracks = []
        if "tracks" in playlist_data:
            for track_data in playlist_data["tracks"]:
                track = Track(
                    track_number=track_data.get("track_number", 0),
                    title=track_data.get("title", "Unknown"),
                    filename=track_data.get("filename", ""),
                    file_path=track_data.get("file_path", ""),
                    duration_ms=track_data.get("duration", track_data.get("duration_ms", 0)),
                    artist=track_data.get("artist"),
                    album=track_data.get("album"),
                    id=track_data.get("id"),
                )
                tracks.append(track)

        # Create playlist domain entity
        playlist = Playlist(
            name=playlist_data.get("title", ""),
            tracks=tracks,
            description=playlist_data.get("description"),
            id=playlist_data.get("id"),
        )

        # Save using pure DDD repository
        saved_playlist = await self._repo.save(playlist)
        logger.info(f"✅ Created playlist: {playlist.name}")
        return saved_playlist.id

    @_handle_repository_errors("playlist_adapter")
    async def get_playlist_by_id(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist by ID using pure DDD principles."""
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist is not None:
            return self._domain_to_dict(playlist)
        return None

    @_handle_repository_errors("playlist_adapter")
    async def get_playlist_by_nfc_tag(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist by NFC tag using pure DDD principles."""
        playlist = await self._repo.find_by_nfc_tag(nfc_tag_id)
        if playlist is not None:
            return self._domain_to_dict(playlist)
        return None

    @_handle_repository_errors("playlist_adapter")
    async def find_by_nfc_tag(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Find playlist by NFC tag ID using pure DDD principles."""
        return await self.get_playlist_by_nfc_tag(nfc_tag_id)

    @_handle_repository_errors("playlist_adapter")
    async def update_nfc_tag_association(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Update NFC tag association using pure DDD principles."""
        return await self._repo.update_nfc_tag_association(playlist_id, nfc_tag_id)

    @_handle_repository_errors("playlist_adapter")
    async def remove_nfc_tag_association(self, nfc_tag_id: str) -> bool:
        """Remove NFC tag association using pure DDD principles."""
        return await self._repo.remove_nfc_tag_association(nfc_tag_id)

    @_handle_repository_errors("playlist_adapter")
    async def find_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all playlists using pure DDD principles."""
        playlists = await self._repo.find_all(limit=limit, offset=offset)
        return [self._domain_to_dict(p) for p in playlists]

    @_handle_repository_errors("playlist_adapter")
    async def count(self) -> int:
        """Count playlists using pure DDD principles."""
        return await self._repo.count()

    @_handle_repository_errors("playlist_adapter")
    async def add_track(self, playlist_id: str, track_data: Dict[str, Any]) -> bool:
        """Add track to playlist using pure DDD principles."""
        # Get playlist
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist is None:
            logger.error(f"❌ Playlist {playlist_id} not found")
            return False

        # Create track from dict
        track = Track(
            track_number=track_data.get("track_number", 0),
            title=track_data.get("title", ""),
            filename=track_data.get("filename", ""),
            file_path=track_data.get("file_path", ""),
            duration_ms=track_data.get("duration", track_data.get("duration_ms")),
            artist=track_data.get("artist"),
            album=track_data.get("album"),
            id=track_data.get("id"),
        )

        # Add track to playlist (domain logic)
        playlist.add_track(track)

        # Save updated playlist
        await self._repo.update(playlist)

        logger.info(f"✅ Added track '{track.title}' to playlist '{playlist.name}'")
        return True

    @_handle_repository_errors("playlist_adapter")
    async def delete_playlist(self, playlist_id: str) -> bool:
        """Delete playlist using pure DDD principles."""
        logger.info(f"🗑️ Starting deletion of playlist: {playlist_id}")

        # First get playlist info before deletion for filesystem cleanup
        playlist = await self._repo.find_by_id(playlist_id)
        logger.info(f"🗑️ Playlist found for deletion: {playlist is not None}")

        if playlist is not None:
            try:
                # playlist is a domain entity, not a dict
                playlist_title = playlist.name
                playlist_path = playlist.path
                logger.info(f"🗑️ Playlist to delete: '{playlist_title}', path: '{playlist_path}'")
            except Exception as e:
                logger.error(f"🗑️ Error accessing playlist properties: {e}")
                import traceback
                logger.error(f"🗑️ Traceback: {traceback.format_exc()}")
                # Continue anyway, but log the issue
                playlist_title = "UNKNOWN"
                playlist_path = "UNKNOWN"

        # Delete from database
        success = await self._repo.delete(playlist_id)
        logger.info(f"🗑️ Database deletion result: {success}")

        if success and playlist is not None:
            # Also clean up associated filesystem folder using playlist info
            logger.info(f"🗑️ Starting filesystem cleanup...")
            await self._cleanup_playlist_folder_by_data(playlist)
            logger.info(f"✅ Deleted playlist and cleaned up folder: {playlist_id}")
        elif success:
            logger.info(f"✅ Deleted playlist: {playlist_id}")
        else:
            logger.error(f"❌ Failed to delete playlist: {playlist_id}")

        return success

    async def _cleanup_playlist_folder_by_data(self, playlist) -> None:
        """Clean up the filesystem folder associated with a playlist using playlist data."""
        try:
            from app.src.config import config as app_config
            from pathlib import Path
            from app.src.utils.path_utils import normalize_folder_name
            import shutil

            logger.info(f"🧹 Starting folder cleanup for playlist")

            upload_folder = Path(app_config.upload_folder)

            # Get playlist title and path - playlist is a domain entity
            playlist_title = playlist.name
            playlist_path = playlist.path
            playlist_id = playlist.id

            logger.info(f"🧹 Playlist data: title='{playlist_title}', path='{playlist_path}', id='{playlist_id}'")

            # List of possible folder names to check
            possible_folders = []

            # 1. Use the stored path (new format)
            if playlist_path:
                folder_path = upload_folder / playlist_path
                possible_folders.append(folder_path)
                logger.debug(f"🧹 Added path from DB: {folder_path}")

            # 2. Try normalized path based on title (in case path is missing)
            if playlist_title:
                normalized_path = normalize_folder_name(playlist_title)
                folder_path = upload_folder / normalized_path
                possible_folders.append(folder_path)
                logger.debug(f"🧹 Added normalized path: {folder_path}")

                # 3. Try original title as folder name (old format)
                folder_path = upload_folder / playlist_title
                possible_folders.append(folder_path)
                logger.debug(f"🧹 Added original title path: {folder_path}")

            # 4. Fallback: try playlist ID as folder name
            if playlist_id:
                folder_path = upload_folder / playlist_id
                possible_folders.append(folder_path)
                logger.debug(f"🧹 Added ID path: {folder_path}")

            logger.debug(f"🧹 Total possible folders to check: {len(possible_folders)}")

            # Try to remove any of the possible folders
            removed_folders = []
            for i, folder_path in enumerate(possible_folders):
                logger.debug(f"🧹 Checking folder {i+1}/{len(possible_folders)}: {folder_path}")
                logger.debug(f"🧹 Folder exists: {folder_path.exists()}, is_dir: {folder_path.is_dir() if folder_path.exists() else 'N/A'}")

                if folder_path.exists() and folder_path.is_dir():
                    logger.info(f"🧹 Removing folder: {folder_path}")
                    shutil.rmtree(folder_path)
                    removed_folders.append(str(folder_path))
                    logger.info(f"🗂️ Removed playlist folder: {folder_path}")

            if not removed_folders:
                logger.warning(f"📁 No folder found to clean up for playlist: {playlist_title}")
            elif len(removed_folders) > 1:
                logger.info(f"🗂️ Removed multiple folders: {removed_folders}")
            else:
                logger.info(f"🗂️ Removed folder: {removed_folders[0]}")

        except Exception as e:
            logger.error(f"⚠️ Failed to clean up folder for playlist {playlist_title}: {e}")
            import traceback
            logger.error(f"⚠️ Traceback: {traceback.format_exc()}")
            # Don't fail the delete operation if folder cleanup fails

    async def _cleanup_playlist_folder(self, playlist_id: str) -> None:
        """Clean up the filesystem folder associated with a playlist (legacy method)."""
        # This method is kept for backward compatibility
        # Get playlist data first, then use the new method
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist:
            await self._cleanup_playlist_folder_by_data(playlist)
        else:
            logger.warning(f"⚠️ Could not find playlist data for cleanup: {playlist_id}")

    @_handle_repository_errors("playlist_adapter")
    async def associate_nfc_tag(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Associate NFC tag with playlist using pure DDD principles."""
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist is None:
            return False

        playlist.nfc_tag_id = nfc_tag_id
        await self._repo.update(playlist)
        return True

    @_handle_repository_errors("playlist_adapter")
    async def disassociate_nfc_tag(self, playlist_id: str) -> bool:
        """Disassociate NFC tag from playlist using pure DDD principles."""
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist is None:
            return False

        playlist.nfc_tag_id = None
        await self._repo.update(playlist)
        return True

    @_handle_repository_errors("playlist_adapter")
    async def get_all_playlists(self, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all playlists using pure DDD principles."""
        playlists = await self._repo.find_all(limit=limit, offset=offset)
        return [self._domain_to_dict(p) for p in playlists]

    @_handle_repository_errors("playlist_adapter")
    async def update_playlist(self, playlist_id: str, updates: Dict[str, Any]) -> bool:
        """Update playlist using pure DDD principles."""
        # Get existing playlist
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist is None:
            logger.error(f"❌ Playlist {playlist_id} not found")
            return False

        # Apply updates to domain entity
        if "title" in updates:
            playlist.name = updates["title"]
        if "name" in updates:
            playlist.name = updates["name"]
        if "description" in updates:
            playlist.description = updates["description"]
        if "nfc_tag_id" in updates:
            playlist.nfc_tag_id = updates["nfc_tag_id"]

        # Save updated playlist
        await self._repo.update(playlist)
        logger.info(f"✅ Updated playlist '{playlist.name}' ({playlist_id})")
        return True

    @_handle_repository_errors("playlist_adapter")
    async def replace_tracks(self, playlist_id: str, tracks_data: List[Dict[str, Any]]) -> bool:
        """Replace all tracks in a playlist using pure DDD principles."""
        # Get existing playlist
        playlist = await self._repo.find_by_id(playlist_id)
        if playlist is None:
            logger.error(f"❌ Playlist {playlist_id} not found")
            return False

        # Clear existing tracks and add new ones
        playlist.tracks = []

        for track_data in tracks_data:
            track = Track(
                track_number=track_data.get("track_number", 0),
                title=track_data.get("title", "Unknown"),
                filename=track_data.get("filename", ""),
                file_path=track_data.get("file_path", ""),
                duration_ms=track_data.get("duration", track_data.get("duration_ms", 0)),
                artist=track_data.get("artist"),
                album=track_data.get("album"),
                id=track_data.get("id"),
            )
            playlist.add_track(track)

        # Save updated playlist
        await self._repo.update(playlist)
        logger.info(f"✅ Replaced tracks for playlist '{playlist.name}' with {len(tracks_data)} tracks")
        return True

    @_handle_repository_errors("playlist_adapter")
    async def update_track_numbers(self, playlist_id: str, track_number_mapping: Dict[int, int]) -> bool:
        """Update track numbers for reordering using pure DDD principles.

        Args:
            playlist_id: Playlist identifier
            track_number_mapping: Dictionary mapping old track numbers to new track numbers

        Returns:
            True if successful, False otherwise
        """
        # Delegate to the repository implementation
        success = await self._repo.update_track_numbers(playlist_id, track_number_mapping)

        if success:
            logger.info(
                f"✅ Updated track numbers for playlist {playlist_id}: {len(track_number_mapping)} tracks"
            )
        else:
            logger.error(
                f"❌ Failed to update track numbers for playlist {playlist_id}"
            )

        return success

    def _domain_to_dict(self, playlist: Playlist) -> Dict[str, Any]:
        """Convert domain model to dict format for API compatibility."""
        return {
            "id": playlist.id,
            "title": playlist.name,  # API compatibility
            "name": playlist.name,   # Domain model field
            "description": playlist.description,
            "nfc_tag_id": playlist.nfc_tag_id,
            "path": playlist.path,   # Folder path for uploads
            "created_at": None,  # Domain model doesn't have timestamps
            "updated_at": None,  # Domain model doesn't have timestamps
            "tracks": [self._track_to_dict(track) for track in playlist.tracks],
        }

    def _track_to_dict(self, track: Track) -> Dict[str, Any]:
        """Convert track domain model to dict format for API compatibility."""
        return {
            "id": track.id,
            "track_number": track.track_number,
            "title": track.title,
            "filename": track.filename,
            "file_path": track.file_path,
            "duration_ms": track.duration_ms,
            "artist": track.artist,
            "album": track.album,
        }
