# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Pure DDD SQLite Playlist Repository

Clean implementation of playlist repository following DDD principles.
Uses DatabaseManager for connection management and focuses only on data access.
"""

import uuid
from typing import List, Optional
import logging
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.domain.repositories.playlist_repository_interface import PlaylistRepositoryProtocol
from app.src.dependencies import get_database_manager
from app.src.services.error.unified_error_decorator import handle_repository_errors

logger = logging.getLogger(__name__)

def _handle_repository_errors(entity_name: str):
    return handle_repository_errors(entity_name)


class PureSQLitePlaylistRepository(PlaylistRepositoryProtocol):
    """Pure DDD SQLite playlist repository implementation.

    This repository implementation follows DDD principles:
    - Only handles data persistence concerns
    - Uses DatabaseManager for all connection management
    - No mixed concerns (transaction management is in DatabaseService)
    - Implements domain repository interface
    """

    def __init__(self):
        """Initialize pure DDD playlist repository.

        Gets database service from DatabaseManager singleton.
        No direct database path management - delegated to infrastructure service.
        """
        self._database_manager = get_database_manager()
        self._db_service = self._database_manager.database_service
        logger.info("✅ Pure DDD SQLite Playlist Repository initialized")

    @_handle_repository_errors("playlist")
    async def save(self, playlist: Playlist) -> Playlist:
        """Save a playlist using pure DDD principles.

        Args:
            playlist: Playlist domain entity to save

        Returns:
            Saved playlist entity with ID assigned
        """
        # Assign ID if not present (domain concern)
        if not playlist.id:
            playlist.id = str(uuid.uuid4())

        # Save playlist data with consistent path generation
        from app.src.utils.path_utils import normalize_folder_name
        path = normalize_folder_name(playlist.title)

        playlist_command = """
            INSERT OR REPLACE INTO playlists
            (id, title, description, nfc_tag_id, path, type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        playlist_params = (
            playlist.id,
            playlist.title,
            playlist.description,
            playlist.nfc_tag_id,
            path,
            "album",
        )

        # Prepare batch operations for atomic transaction
        operations = [
            {
                "query": playlist_command,
                "params": playlist_params,
                "type": "command"
            },
            {
                "query": "DELETE FROM tracks WHERE playlist_id = ?",
                "params": (playlist.id,),
                "type": "command"
            }
        ]

        # Add track insertions
        for track in playlist.tracks:
            track_command = """
                INSERT INTO tracks
                (id, playlist_id, track_number, title, filename, file_path, duration_ms, artist, album, created_at, updated_at, play_count, server_seq)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 0)
            """
            track_params = (
                track.id or str(uuid.uuid4()),
                playlist.id,
                track.track_number,
                track.title,
                track.filename,
                track.file_path,
                track.duration_ms,
                track.artist,
                track.album,
            )
            operations.append({
                "query": track_command,
                "params": track_params,
                "type": "command"
            })

        # Execute all operations in a single transaction
        self._db_service.execute_batch(operations, f"save_playlist_{playlist.id}")

        logger.info(f"✅ Saved playlist: {playlist.title}")
        return playlist

    async def find_by_id(self, playlist_id: str) -> Optional[Playlist]:
        """Find playlist by ID using pure DDD principles.

        Args:
            playlist_id: Unique identifier

        Returns:
            Playlist domain entity or None if not found
        """
        import asyncio
        # Force async context (required for proper async/await behavior with synchronous code)
        await asyncio.sleep(0)

        # Get playlist data
        playlist_query = "SELECT * FROM playlists WHERE id = ?"
        playlist_row = self._db_service.execute_single(
            playlist_query,
            (playlist_id,),
            f"find_playlist_{playlist_id}"
        )

        if not playlist_row:
            return None

        # Get tracks data
        tracks_query = """
            SELECT * FROM tracks
            WHERE playlist_id = ?
            ORDER BY track_number
        """
        track_rows = self._db_service.execute_query(
            tracks_query,
            (playlist_id,),
            f"find_tracks_for_playlist_{playlist_id}"
        )

        return self._build_playlist_from_rows(playlist_row, track_rows)

    async def exists(self, playlist_id: str) -> bool:
        """Check if a playlist exists.

        Args:
            playlist_id: Unique identifier

        Returns:
            True if playlist exists, False otherwise
        """
        import asyncio
        await asyncio.sleep(0)

        playlist_query = "SELECT 1 FROM playlists WHERE id = ? LIMIT 1"
        result = self._db_service.execute_single(
            playlist_query,
            (playlist_id,),
            f"exists_playlist_{playlist_id}"
        )
        return result is not None

    @_handle_repository_errors("playlist")
    async def find_by_name(self, name: str) -> Optional[Playlist]:
        """Find playlist by name using pure DDD principles.

        Args:
            name: Playlist name

        Returns:
            Playlist domain entity or None if not found
        """
        playlist_query = "SELECT * FROM playlists WHERE title = ?"
        playlist_row = self._db_service.execute_single(
            playlist_query,
            (name,),
            f"find_playlist_by_name_{name}"
        )

        if not playlist_row:
            return None

        # Get tracks for this playlist
        tracks_query = """
            SELECT * FROM tracks
            WHERE playlist_id = ?
            ORDER BY track_number
        """
        track_rows = self._db_service.execute_query(
            tracks_query,
            (playlist_row["id"],),
            f"find_tracks_for_playlist_{playlist_row['id']}"
        )

        return self._build_playlist_from_rows(playlist_row, track_rows)

    @_handle_repository_errors("playlist")
    async def find_by_nfc_tag(self, nfc_tag_id: str) -> Optional[Playlist]:
        """Find playlist by NFC tag using pure DDD principles.

        Args:
            nfc_tag_id: NFC tag identifier

        Returns:
            Playlist domain entity or None if not found
        """
        playlist_query = "SELECT * FROM playlists WHERE nfc_tag_id = ?"
        playlist_row = self._db_service.execute_single(
            playlist_query,
            (nfc_tag_id,),
            f"find_playlist_by_nfc_{nfc_tag_id}"
        )

        if not playlist_row:
            return None

        # Get tracks for this playlist
        tracks_query = """
            SELECT * FROM tracks
            WHERE playlist_id = ?
            ORDER BY track_number
        """
        track_rows = self._db_service.execute_query(
            tracks_query,
            (playlist_row["id"],),
            f"find_tracks_for_playlist_{playlist_row['id']}"
        )

        return self._build_playlist_from_rows(playlist_row, track_rows)

    @_handle_repository_errors("playlist")
    async def find_all(self, limit: int = None, offset: int = 0) -> List[Playlist]:
        """Find all playlists with pagination using pure DDD principles.

        Args:
            limit: Maximum number of playlists to return
            offset: Number of playlists to skip

        Returns:
            List of playlist domain entities
        """
        query = "SELECT * FROM playlists ORDER BY updated_at DESC"
        params = []

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        if offset > 0:
            query += " OFFSET ?"
            params.append(offset)

        playlist_rows = self._db_service.execute_query(
            query,
            tuple(params),
            f"find_all_playlists_limit_{limit}_offset_{offset}"
        )

        playlists = []
        for playlist_row in playlist_rows:
            # Get tracks for each playlist
            tracks_query = """
                SELECT * FROM tracks
                WHERE playlist_id = ?
                ORDER BY track_number
            """
            track_rows = self._db_service.execute_query(
                tracks_query,
                (playlist_row["id"],),
                f"find_tracks_for_playlist_{playlist_row['id']}"
            )

            playlist = self._build_playlist_from_rows(playlist_row, track_rows)
            playlists.append(playlist)

        return playlists

    async def update(self, playlist: Playlist) -> Playlist:
        """Update existing playlist using pure DDD principles.

        Args:
            playlist: Updated playlist domain entity

        Returns:
            Updated playlist entity
        """
        # For this implementation, update is same as save with REPLACE
        return await self.save(playlist)

    @_handle_repository_errors("playlist")
    async def delete(self, playlist_id: str) -> bool:
        """Delete playlist by ID using pure DDD principles.

        Args:
            playlist_id: Playlist identifier

        Returns:
            True if deleted, False if not found
        """
        delete_command = "DELETE FROM playlists WHERE id = ?"
        affected_rows = self._db_service.execute_command(
            delete_command,
            (playlist_id,),
            f"delete_playlist_{playlist_id}"
        )

        deleted = affected_rows > 0
        if deleted:
            logger.info(f"✅ Deleted playlist: {playlist_id}")

        return deleted

    @_handle_repository_errors("playlist")
    async def count(self) -> int:
        """Count total playlists using pure DDD principles.

        Returns:
            Total playlist count
        """
        count_query = "SELECT COUNT(*) FROM playlists"
        result = self._db_service.execute_single(count_query, None, "count_playlists")
        return result[0] if result else 0

    @_handle_repository_errors("playlist")
    async def search(self, query: str, limit: int = None) -> List[Playlist]:
        """Search playlists by name or description using pure DDD principles.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching playlist domain entities
        """
        search_query = """
            SELECT * FROM playlists
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY updated_at DESC
        """
        params = [f"%{query}%", f"%{query}%"]

        if limit is not None:
            search_query += " LIMIT ?"
            params.append(limit)

        playlist_rows = self._db_service.execute_query(
            search_query,
            tuple(params),
            f"search_playlists_{query}"
        )

        playlists = []
        for playlist_row in playlist_rows:
            # Get tracks for each playlist
            tracks_query = """
                SELECT * FROM tracks
                WHERE playlist_id = ?
                ORDER BY track_number
            """
            track_rows = self._db_service.execute_query(
                tracks_query,
                (playlist_row["id"],),
                f"find_tracks_for_playlist_{playlist_row['id']}"
            )

            playlist = self._build_playlist_from_rows(playlist_row, track_rows)
            playlists.append(playlist)

        return playlists

    @_handle_repository_errors("playlist")
    async def update_nfc_tag_association(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Update NFC tag association for a playlist.

        Args:
            playlist_id: Playlist ID to associate
            nfc_tag_id: NFC tag identifier

        Returns:
            True if update successful, False otherwise
        """
        # Execute operations in batch transaction for atomicity
        operations = [
            {
                "query": "UPDATE playlists SET nfc_tag_id = NULL, updated_at = CURRENT_TIMESTAMP WHERE nfc_tag_id = ?",
                "params": (nfc_tag_id,),
                "type": "command"
            },
            {
                "query": "UPDATE playlists SET nfc_tag_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                "params": (nfc_tag_id, playlist_id),
                "type": "command"
            }
        ]

        results = self._db_service.execute_batch(
            operations,
            f"update_nfc_association_{playlist_id}_{nfc_tag_id}"
        )

        # Check if the second operation (actual association) affected any rows
        success = results[1] > 0 if len(results) > 1 else False

        if success:
            logger.info(
                f"✅ Updated playlist {playlist_id} with NFC tag {nfc_tag_id}"
            )
        else:
            logger.warning(
                f"⚠️ No playlist found with ID {playlist_id}"
            )

        return success

    @_handle_repository_errors("playlist")
    async def remove_nfc_tag_association(self, nfc_tag_id: str) -> bool:
        """Remove NFC tag association from any playlist.

        Args:
            nfc_tag_id: NFC tag identifier to unassociate

        Returns:
            True if removal successful
        """
        remove_command = """
            UPDATE playlists
            SET nfc_tag_id = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE nfc_tag_id = ?
        """

        self._db_service.execute_command(
            remove_command,
            (nfc_tag_id,),
            f"remove_nfc_association_{nfc_tag_id}"
        )

        logger.info(f"✅ Removed NFC tag {nfc_tag_id} from all playlists")
        return True

    @_handle_repository_errors("playlist")
    async def update_track_numbers(self, playlist_id: str, track_number_mapping: dict) -> bool:
        """Update track numbers for tracks in a playlist.

        This method efficiently updates track numbers using UPDATE statements
        instead of deleting and reinserting tracks.

        Args:
            playlist_id: Playlist identifier
            track_number_mapping: Dictionary mapping old track numbers to new track numbers

        Returns:
            True if successful, False otherwise
        """
        if not track_number_mapping:
            logger.warning("Empty track number mapping provided")
            return False

        try:
            # Use transaction to ensure atomicity
            async def update_operation():
                # First, temporarily set all track numbers to negative values to avoid conflicts
                temp_mapping = {}
                for old_num, new_num in track_number_mapping.items():
                    temp_mapping[old_num] = -new_num

                # Step 1: Update to temporary negative values
                for old_num, temp_num in temp_mapping.items():
                    await self._db_service.execute(
                        """
                        UPDATE tracks
                        SET track_number = ?
                        WHERE playlist_id = ? AND track_number = ?
                        """,
                        (temp_num, playlist_id, old_num),
                        f"temp_update_track_{playlist_id}_{old_num}"
                    )

                # Step 2: Update from temporary values to final values
                for old_num, new_num in track_number_mapping.items():
                    await self._db_service.execute(
                        """
                        UPDATE tracks
                        SET track_number = ?
                        WHERE playlist_id = ? AND track_number = ?
                        """,
                        (new_num, playlist_id, -new_num),
                        f"final_update_track_{playlist_id}_{new_num}"
                    )

                return True

            # Execute within transaction
            result = await self._db_service.transaction(update_operation)

            if result:
                logger.info(
                    f"✅ Updated track numbers for playlist {playlist_id}: {len(track_number_mapping)} tracks reordered"
                )
            else:
                logger.error(f"❌ Failed to update track numbers for playlist {playlist_id}"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Error updating track numbers for playlist {playlist_id}: {e}"
            )
            return False

    def _build_playlist_from_rows(self, playlist_row, track_rows) -> Playlist:
        """Build playlist domain entity from database rows.

        Args:
            playlist_row: SQLite playlist row
            track_rows: List of SQLite track rows

        Returns:
            Playlist domain entity
        """
        tracks = []
        for track_row in track_rows:
            # Generate file_path if missing but filename exists
            file_path = track_row["file_path"] if track_row["file_path"] else ""
            filename = track_row["filename"] if track_row["filename"] else ""

            if not file_path and filename:
                # Use playlist title to generate file_path
                playlist_folder = (
                    playlist_row["title"]
                    if playlist_row["title"]
                    else "Unknown"
                )
                try:
                    from app.src.config import config
                    from pathlib import Path

                    file_path = str(Path(config.upload_folder) / playlist_folder / filename)
                except:
                    # Fallback if config not available
                    file_path = f"./uploads/{playlist_folder}/{filename}"

            track = Track(
                id=track_row["id"],
                track_number=track_row["track_number"] if track_row["track_number"] else 1,
                title=track_row["title"] if track_row["title"] else "Unknown",
                filename=filename,
                file_path=file_path,
                duration_ms=track_row["duration_ms"] if track_row["duration_ms"] else None,
                artist=track_row["artist"] if track_row["artist"] else None,
                album=track_row["album"] if track_row["album"] else None,
            )
            tracks.append(track)

        # Build playlist domain entity
        playlist = Playlist(
            id=playlist_row["id"],
            title=playlist_row["title"],  # Contract-compliant field mapping
            description=playlist_row["description"],
            nfc_tag_id=playlist_row["nfc_tag_id"],
            path=playlist_row["path"],
            tracks=tracks,
        )

        return playlist

    @_handle_repository_errors("tracks")
    async def get_by_playlist(self, playlist_id: str) -> List[Track]:
        """Alias for get_tracks_by_playlist - used by TrackService.

        Args:
            playlist_id: Playlist identifier

        Returns:
            List of track domain entities
        """
        return await self.get_tracks_by_playlist(playlist_id)

    async def get_tracks_by_playlist(self, playlist_id: str) -> List[Track]:
        """Get all tracks for a specific playlist.

        Args:
            playlist_id: Playlist identifier

        Returns:
            List of track domain entities
        """
        import asyncio
        await asyncio.sleep(0)

        tracks_query = """
            SELECT * FROM tracks
            WHERE playlist_id = ?
            ORDER BY track_number
        """
        track_rows = self._db_service.execute_query(
            tracks_query,
            (playlist_id,),
            f"get_tracks_by_playlist_{playlist_id}"
        )

        tracks = []
        for track_row in track_rows:
            # Generate file_path if missing but filename exists
            file_path = track_row["file_path"] if track_row["file_path"] else ""
            filename = track_row["filename"] if track_row["filename"] else ""

            if not file_path and filename:
                # Fallback path generation
                try:
                    from app.src.config import config
                    from pathlib import Path
                    file_path = str(Path(config.upload_folder) / "unknown_playlist" / filename)
                except:
                    file_path = f"./uploads/unknown_playlist/{filename}"

            track = Track(
                id=track_row["id"],
                track_number=track_row["track_number"] if track_row["track_number"] else 1,
                title=track_row["title"] if track_row["title"] else "Unknown",
                filename=filename,
                file_path=file_path,
                duration_ms=track_row["duration_ms"] if track_row["duration_ms"] else None,
                artist=track_row["artist"] if track_row["artist"] else None,
                album=track_row["album"] if track_row["album"] else None,
            )
            tracks.append(track)

        logger.info(f"✅ Retrieved {len(tracks)} tracks for playlist {playlist_id}")
        return tracks

    @_handle_repository_errors("tracks")
    async def delete_tracks_by_playlist(self, playlist_id: str) -> bool:
        """Delete all tracks for a specific playlist.

        Args:
            playlist_id: Playlist identifier

        Returns:
            True if deletion successful
        """
        delete_command = "DELETE FROM tracks WHERE playlist_id = ?"
        affected_rows = self._db_service.execute_command(
            delete_command,
            (playlist_id,),
            f"delete_tracks_by_playlist_{playlist_id}"
        )

        logger.info(f"✅ Deleted {affected_rows} tracks for playlist {playlist_id}")
        return True

    @_handle_repository_errors("track")
    async def get_track_by_id(self, track_id: str) -> Optional[dict]:
        """Get a single track by its ID.

        Args:
            track_id: Track identifier

        Returns:
            Track data dictionary or None if not found
        """
        import asyncio
        await asyncio.sleep(0)

        track_query = "SELECT * FROM tracks WHERE id = ?"
        track_row = self._db_service.execute_single(
            track_query,
            (track_id,),
            f"get_track_by_id_{track_id}"
        )

        if not track_row:
            return None

        # Generate file_path if missing but filename exists
        file_path = track_row["file_path"] if track_row["file_path"] else ""
        filename = track_row["filename"] if track_row["filename"] else ""

        if not file_path and filename:
            try:
                from app.src.config import config
                from pathlib import Path
                file_path = str(Path(config.upload_folder) / "unknown_playlist" / filename)
            except:
                file_path = f"./uploads/unknown_playlist/{filename}"

        # Build track entity and convert to dict
        track = Track(
            id=track_row["id"],
            track_number=track_row["track_number"] if track_row["track_number"] else 1,
            title=track_row["title"] if track_row["title"] else "Unknown",
            filename=filename,
            file_path=file_path,
            duration_ms=track_row["duration_ms"] if track_row["duration_ms"] else None,
            artist=track_row["artist"] if track_row["artist"] else None,
            album=track_row["album"] if track_row["album"] else None,
        )

        # Convert Track entity to dictionary
        from dataclasses import asdict
        return asdict(track)

    @_handle_repository_errors("track")
    async def add_track_to_playlist(self, playlist_id: str, track_data: dict) -> str:
        """Add a track to a playlist.

        Args:
            playlist_id: Playlist identifier
            track_data: Track data dictionary

        Returns:
            The ID of the created track
        """
        import asyncio
        await asyncio.sleep(0)

        # Generate track ID if not provided
        track_id = track_data.get('id', str(uuid.uuid4()))

        track_command = """
            INSERT INTO tracks
            (id, playlist_id, track_number, title, filename, file_path, duration_ms, artist, album, created_at, updated_at, play_count, server_seq)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 0)
        """
        track_params = (
            track_id,
            playlist_id,
            track_data.get('track_number', 1),
            track_data.get('title', 'Unknown Track'),
            track_data.get('filename', ''),
            track_data.get('file_path', ''),
            track_data.get('duration_ms', 0),
            track_data.get('artist'),
            track_data.get('album'),
        )

        self._db_service.execute_command(
            track_command,
            track_params,
            f"add_track_{track_id}_to_playlist_{playlist_id}"
        )

        logger.info(f"✅ Added track {track_data.get('title')} to playlist {playlist_id}")
        return track_id

    @_handle_repository_errors("track")
    async def update_track(self, track_id: str, track_data: dict) -> bool:
        """Update an existing track.

        Args:
            track_id: Track identifier
            track_data: Dictionary containing update fields

        Returns:
            True if update successful
        """
        import asyncio
        await asyncio.sleep(0)

        # Build UPDATE statement dynamically based on provided fields
        update_fields = []
        params = []

        allowed_fields = ['title', 'track_number', 'filename', 'file_path', 'duration_ms', 'artist', 'album']
        for field in allowed_fields:
            if field in track_data:
                update_fields.append(f"{field} = ?")
                params.append(track_data[field])

        if not update_fields:
            logger.warning(f"No valid fields to update for track {track_id}")
            return False

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        # Add track_id to params
        params.append(track_id)

        update_command = f"UPDATE tracks SET {', '.join(update_fields)} WHERE id = ?"
        affected_rows = self._db_service.execute_command(
            update_command,
            tuple(params),
            f"update_track_{track_id}"
        )

        if affected_rows > 0:
            logger.info(f"✅ Updated track {track_id}")
            return True
        else:
            logger.warning(f"❌ Track {track_id} not found for update")
            return False

    @_handle_repository_errors("track")
    async def delete_track(self, track_id: str) -> bool:
        """Delete a track by ID.

        Args:
            track_id: Track identifier

        Returns:
            True if deleted, False if not found
        """
        import asyncio
        await asyncio.sleep(0)

        delete_command = "DELETE FROM tracks WHERE id = ?"
        affected_rows = self._db_service.execute_command(
            delete_command,
            (track_id,),
            f"delete_track_{track_id}"
        )

        deleted = affected_rows > 0
        if deleted:
            logger.info(f"✅ Deleted track {track_id}")
        else:
            logger.warning(f"❌ Track {track_id} not found for deletion")

        return deleted

    @_handle_repository_errors("tracks")
    async def reorder_tracks(self, playlist_id: str, track_orders: list) -> bool:
        """Reorder tracks in a playlist.

        Args:
            playlist_id: Playlist identifier
            track_orders: List of dicts with 'track_id' and 'track_number'

        Returns:
            True if reordering successful
        """
        import asyncio
        await asyncio.sleep(0)

        if not track_orders:
            logger.warning("Empty track orders list provided")
            return False

        # Prepare batch operations for atomic transaction
        operations = []
        for order in track_orders:
            track_id = order.get('track_id')
            track_number = order.get('track_number')

            if not track_id or track_number is None:
                logger.warning(f"Invalid track order entry: {order}")
                continue

            update_command = """
                UPDATE tracks
                SET track_number = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND playlist_id = ?
            """
            operations.append({
                "query": update_command,
                "params": (track_number, track_id, playlist_id),
                "type": "command"
            })

        if not operations:
            logger.warning("No valid track orders to process")
            return False

        # Execute all operations in a single transaction
        self._db_service.execute_batch(operations, f"reorder_tracks_playlist_{playlist_id}")

        logger.info(f"✅ Reordered {len(operations)} tracks in playlist {playlist_id}")
        return True
