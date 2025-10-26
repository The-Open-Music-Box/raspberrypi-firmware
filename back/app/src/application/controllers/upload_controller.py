# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
UploadController

High-level controller to orchestrate chunked uploads using UploadApplicationService,
emitting progress/completion events and updating playlists upon finalization.
"""

from math import ceil
from pathlib import Path
from typing import Dict, Optional

from socketio import AsyncServer

# PURE DOMAIN ARCHITECTURE - No Legacy Services
from app.src.monitoring import get_logger
from app.src.application.services.upload_application_service import UploadApplicationService
from app.src.infrastructure.upload.adapters.file_storage_adapter import LocalFileStorageAdapter
from app.src.infrastructure.upload.adapters.metadata_extractor import MutagenMetadataExtractor
from app.src.services.error.unified_error_decorator import handle_errors


logger = get_logger(__name__)


class UploadController:
    """
    Orchestrates upload sessions and integrates them with playlists.
    """

    def __init__(
        self,
        config,
        data_application_service,
        socketio: Optional[AsyncServer] = None
    ):
        """Initialize UploadController with proper dependency injection.

        Args:
            config: Application configuration object
            data_application_service: Data application service (required, injected)
            socketio: Socket.IO instance for real-time communication (optional)

        Raises:
            TypeError: If data_application_service is None (required dependency)
        """
        if data_application_service is None:
            raise TypeError(
                "data_application_service is required. "
                "Use proper dependency injection instead of lazy loading."
            )

        self.config = config
        self.socketio = socketio
        self.playlist_app_service = data_application_service

        # PURE DOMAIN ARCHITECTURE - Initialize DDD services
        self.file_storage = LocalFileStorageAdapter(base_temp_path=str(config.upload_folder))
        self.metadata_extractor = MutagenMetadataExtractor()

        # Initialize upload application service
        self.upload_app_service = UploadApplicationService(
            file_storage=self.file_storage,
            metadata_extractor=self.metadata_extractor,
            upload_folder=str(config.upload_folder),
        )

    async def init_upload_session(
        self,
        playlist_id: str,
        filename: str,
        file_size: int,
        chunk_size: int,
        file_hash: Optional[str] = None,
    ) -> Dict:
        """
        Initialize a chunked upload session.
        Returns at minimum: session_id, chunk_size, total_chunks.
        """
        total_chunks = int(ceil(file_size / float(chunk_size)))

        # Get playlist path from playlist service
        # Note: get_playlist_use_case returns the playlist dict directly or None
        playlist = await self.playlist_app_service.get_playlist_use_case(playlist_id)
        playlist_path = None
        if playlist:
            playlist_path = playlist.get("path", playlist_id)  # fallback to ID if no path

        # Use domain application service to create session
        result = await self.upload_app_service.create_upload_session_use_case(
            filename=filename,
            total_size=file_size,
            total_chunks=total_chunks,
            playlist_id=playlist_id,
            playlist_path=playlist_path,
        )

        if result.get("status") != "success":
            logger.error(f"Failed to create upload session: {result.get('message')}")
            return {"error": result.get("message", "Failed to create session")}

        session = result.get("session", {})
        session_id = session.get("session_id")

        logger.info(f"Upload session created: {session_id} for playlist {playlist_id}"
        )
        return {
            "session_id": session_id,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
        }

    @handle_errors("upload_chunk")
    async def upload_chunk(
        self, playlist_id: str, session_id: str, chunk_index: int, chunk_data: bytes
    ) -> Dict:
        """
        Process a single chunk and emit upload:progress events.
        """
        # Use domain application service to upload chunk
        result = await self.upload_app_service.upload_chunk_use_case(
            session_id=session_id, chunk_index=chunk_index, chunk_data=chunk_data
        )

        if result.get("status") == "success":
            session = result.get("session", {})
            progress = result.get("progress", 0)
            complete = session.get("status") == "completed"

            # Emit progress event (if socket available)
            if self.socketio:
                await self.socketio.emit(
                    "upload:progress",
                    {
                        "playlist_id": playlist_id,
                        "session_id": session_id,
                        "chunk_index": chunk_index,
                        "progress": progress,
                        "complete": complete,
                    },
                    room=f"playlist:{playlist_id}",
                )
        return result

    async def get_session_status(self, session_id: str) -> Dict:
        """
        Return current status for the given upload session.
        """
        result = await self.upload_app_service.get_upload_status_use_case(session_id)
        if result.get("status") == "success":
            return result.get("session", {})
        else:
            return {"error": result.get("message", "Session not found")}

    @handle_errors("finalize_upload")
    @handle_errors("finalize_upload")
    async def finalize_upload(
        self,
        playlist_id: str,
        session_id: str,
        file_hash: Optional[str] = None,
        metadata_override: Optional[Dict] = None,
    ) -> Dict:
        """
        Finalize the upload: assemble chunks, extract metadata, and add track to playlist.
        Returns: { status: 'success'|'error', track?: {...}, message? }
        """
        try:
            # Check upload completion status from application service
            logger.info(f"🔍 Checking upload status for session {session_id}")
            status_result = await self.upload_app_service.get_upload_status_use_case(session_id)

            if status_result.get("status") != "success":
                logger.error(f"❌ Upload session not found: {status_result}")
                return {"status": "error", "message": "Upload session not found"}

            session = status_result.get("session", {})
            logger.info(f"📋 Session status: {session.get('status')}")

            if session.get("status") != "completed":
                logger.error(f"❌ Upload not completed yet. Current status: {session.get('status')}",
                )
                return {"status": "error", "message": "Upload not completed yet"}

            # Get completion result (includes assembled file path and metadata)
            completion_data = session.get("completion_data", {})
            logger.info(f"📦 Completion data status: {completion_data.get('completion_status')}",
            )

            if completion_data.get("completion_status") != "success":
                logger.error(f"❌ Upload completion failed: {completion_data}")
                return {"status": "error", "message": "Upload completion failed"}

            file_path = completion_data.get("file_path")
            metadata_dict = completion_data.get("metadata", {})
            filename = Path(file_path).name

            # Resolve playlist folder path using domain service
            playlist = await self.playlist_app_service.get_playlist_use_case(playlist_id)
            if not playlist:
                logger.error(f"❌ Playlist not found: {playlist_id}")
                return {"status": "error", "message": "Playlist not found"}

            # Build track entry for domain controller integration
            current_tracks = playlist.get("tracks", [])
            new_track_number = len(current_tracks) + 1
            # Duration should already be in milliseconds from the domain service
            duration_ms = metadata_dict.get("duration", 0)

            track_entry = {
                "track_number": new_track_number,
                "title": (metadata_override or {}).get("title")
                or metadata_dict.get("title")
                or Path(filename).stem,
                "filename": filename,
                "file_path": str(file_path),
                "duration": duration_ms,
                "artist": (metadata_override or {}).get("artist") or metadata_dict.get("artist"),
                "album": (metadata_override or {}).get("album") or metadata_dict.get("album"),
                "file_size": metadata_dict.get("file_size"),
            }

            logger.info(f"✅ Upload finalized, track ready for domain integration: {track_entry.get('title')}",
            )

            # Emit completion event
            await self.socketio.emit(
                "upload:complete",
                {
                    "playlist_id": playlist_id,
                    "session_id": session_id,
                    "filename": filename,
                    "metadata": metadata_dict,
                    "track": track_entry,
                },
                room=f"playlist:{playlist_id}",
            )

            return {"status": "success", "track": track_entry}

        except Exception as e:
            logger.error(f"Finalize upload failed: {e}")
            if self.socketio:
                await self.socketio.emit(
                    "upload:error",
                    {"playlist_id": playlist_id, "session_id": session_id, "error": str(e)},
                    room=f"playlist:{playlist_id}",
                )
            return {"status": "error", "message": str(e)}
