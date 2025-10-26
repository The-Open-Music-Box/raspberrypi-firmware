# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Upload Application Service - Use Cases Orchestration."""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any

from app.src.domain.upload.entities.upload_session import UploadSession, UploadStatus
from app.src.domain.upload.value_objects.file_chunk import FileChunk
from app.src.domain.upload.services.upload_validation_service import UploadValidationService
from app.src.domain.upload.protocols.file_storage_protocol import (
    FileStorageProtocol,
    MetadataExtractionProtocol,
)
from app.src.services.error.unified_error_decorator import handle_service_errors
import logging

logger = logging.getLogger(__name__)


class UploadApplicationService:
    """Application service orchestrating upload use cases.

    Coordinates between domain services, storage adapters, and external
    systems to implement complete upload-related use cases.
    """

    def __init__(
        self,
        file_storage: FileStorageProtocol,
        metadata_extractor: MetadataExtractionProtocol,
        validation_service: Optional[UploadValidationService] = None,
        upload_folder: str = "uploads",
    ):
        """Initialize upload application service.

        Args:
            file_storage: Storage adapter for file operations
            metadata_extractor: Metadata extraction adapter
            validation_service: Domain validation service
            upload_folder: Base folder for uploads
        """
        self._file_storage = file_storage
        self._metadata_extractor = metadata_extractor
        self._validation_service = validation_service or UploadValidationService()
        self._upload_folder = Path(upload_folder)

        # Session management
        self._active_sessions: Dict[str, UploadSession] = {}

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_upload_service(self) -> Dict[str, Any]:
        """Start the upload service.

        Returns:
            Status dictionary
        """
        # Ensure upload folder exists
        self._upload_folder.mkdir(parents=True, exist_ok=True)
        # Start cleanup task for expired sessions
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("✅ Upload service started successfully")
        return {
            "status": "success",
            "message": "Upload service started",
            "upload_folder": str(self._upload_folder),
            "supported_formats": self._metadata_extractor.get_supported_formats(),
        }

    async def create_upload_session_use_case(
        self, filename: str, total_size: int, total_chunks: int, playlist_id: Optional[str] = None, playlist_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use case: Create a new upload session.

        Args:
            filename: Name of file to upload
            total_size: Total file size in bytes
            total_chunks: Number of chunks expected
            playlist_id: Optional playlist to associate with
            playlist_path: Optional playlist folder path for file storage

        Returns:
            Result dictionary with session info
        """
        # Validate upload request
        validation_result = self._validation_service.validate_upload_request(
            filename, total_size, total_chunks, playlist_id
        )
        if not validation_result["valid"]:
            return {
                "status": "error",
                "message": "Upload request validation failed",
                "errors": validation_result["errors"],
                "error_type": "validation_error",
            }
        # Create upload session
        session = UploadSession(
            filename=filename,
            total_chunks=total_chunks,
            total_size_bytes=total_size,
            playlist_id=playlist_id,
            playlist_path=playlist_path,
        )
        # Create session directory
        await self._file_storage.create_session_directory(session.session_id)
        # Track session
        self._active_sessions[session.session_id] = session
        logger.info(f"✅ Created upload session {session.session_id} for {filename}")
        result = {
            "status": "success",
            "message": "Upload session created",
            "session": session.to_dict(),
        }
        # Include warnings if any
        if validation_result["warnings"]:
            result["warnings"] = validation_result["warnings"]
        return result

    async def upload_chunk_use_case(
        self, session_id: str, chunk_index: int, chunk_data: bytes
    ) -> Dict[str, Any]:
        """Use case: Upload a file chunk.

        Args:
            session_id: Upload session ID
            chunk_index: Index of chunk in sequence
            chunk_data: Chunk data bytes

        Returns:
            Result dictionary with upload progress
        """
        # Get session
        session = self._active_sessions.get(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Upload session not found",
                "error_type": "not_found",
            }
        # Create chunk
        chunk = FileChunk.create(chunk_index, chunk_data)
        # Validate chunk
        validation_result = self._validation_service.validate_chunk(chunk, session)
        if not validation_result["valid"]:
            return {
                "status": "error",
                "message": "Chunk validation failed",
                "errors": validation_result["errors"],
                "error_type": "validation_error",
            }
        # Store chunk
        await self._file_storage.store_chunk(session_id, chunk)
        # Update session
        session.add_chunk(chunk)
        logger.debug(
            f"📦 Chunk {chunk_index} uploaded for session {session_id} ({session.progress_percentage:.1f}%)"
        )
        result = {
            "status": "success",
            "message": "Chunk uploaded successfully",
            "session": session.to_dict(),
            "chunk_index": chunk_index,
            "progress": session.progress_percentage,
        }
        # Check if upload is complete
        if session.status == UploadStatus.COMPLETED:
            completion_result = await self._handle_upload_completion(session)
            # Store completion data in session for later retrieval
            session.completion_data = completion_result
            # Persist the modified session in the active sessions store
            self._active_sessions[session.session_id] = session
            result.update(completion_result)
        return result

    async def get_upload_status_use_case(self, session_id: str) -> Dict[str, Any]:
        """Use case: Get upload session status.

        Args:
            session_id: Upload session ID

        Returns:
            Session status dictionary
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Upload session not found",
                "error_type": "not_found",
            }
        return {"status": "success", "session": session.to_dict()}

    async def cancel_upload_use_case(self, session_id: str) -> Dict[str, Any]:
        """Use case: Cancel an upload session.

        Args:
            session_id: Upload session ID to cancel

        Returns:
            Cancellation result dictionary
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Upload session not found",
                "error_type": "not_found",
            }
        # Mark session as cancelled
        session.mark_cancelled()
        # Cleanup session files
        await self._file_storage.cleanup_session(session_id)
        logger.info(f"🛑 Cancelled upload session {session_id}")
        return {
            "status": "success",
            "message": "Upload session cancelled",
            "session_id": session_id,
        }

    async def list_active_uploads_use_case(self) -> Dict[str, Any]:
        """Use case: List all active upload sessions.

        Returns:
            List of active sessions
        """
        active_sessions = [
            session.to_dict() for session in self._active_sessions.values() if session.is_active()
        ]
        return {
            "status": "success",
            "active_sessions": active_sessions,
            "count": len(active_sessions),
        }

    async def _handle_upload_completion(self, session: UploadSession) -> Dict[str, Any]:
        """Handle completion of an upload session.

        Args:
            session: Completed upload session

        Returns:
            Completion result dictionary
        """
        # Validate session completion
        validation_result = self._validation_service.validate_session_completion(session)
        if not validation_result["valid"]:
            session.mark_failed("Session completion validation failed")
            return {"completion_status": "failed", "completion_errors": validation_result["errors"]}
        # Assemble file - use playlist_path if available, fallback to playlist_id
        playlist_folder = getattr(session, 'playlist_path', None) or session.playlist_id
        output_path = self._upload_folder / playlist_folder / session.filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        assembled_path = await self._file_storage.assemble_file(session, output_path)
        # Verify file integrity
        integrity_ok = await self._file_storage.verify_file_integrity(
            assembled_path, session.total_size_bytes
        )
        if not integrity_ok:
            session.mark_failed("File integrity check failed")
            return {
                "completion_status": "failed",
                "completion_errors": ["File integrity verification failed"],
            }
        # Extract metadata
        metadata = await self._metadata_extractor.extract_metadata(assembled_path)
        session.set_metadata(metadata)
        # Validate metadata
        metadata_validation = self._validation_service.validate_audio_metadata(metadata)
        # Cleanup temporary files
        await self._file_storage.cleanup_session(session.session_id)
        logger.info(f"🎉 Upload completed successfully: {session.filename}")
        result = {
            "completion_status": "success",
            "file_path": str(assembled_path),
            "metadata": metadata.to_dict(),
            "metadata_validation": metadata_validation,
        }
        return result

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                expired_sessions = []
                for session_id, session in self._active_sessions.items():
                    if session.is_expired() and session.status in [
                        UploadStatus.CREATED,
                        UploadStatus.IN_PROGRESS,
                    ]:
                        session.mark_expired()
                        expired_sessions.append(session_id)

                # Cleanup expired sessions
                for session_id in expired_sessions:
                    await self._file_storage.cleanup_session(session_id)
                if expired_sessions:
                    logger.info(
                        f"🧹 Cleaned up {len(expired_sessions)} expired upload sessions"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"⚠️ Error in upload cleanup: {e}")
