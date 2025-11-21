# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""File Storage Adapter Implementation."""

import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from app.src.domain.upload.protocols.file_storage_protocol import FileStorageProtocol
from app.src.domain.upload.value_objects.file_chunk import FileChunk
from app.src.domain.upload.entities.upload_session import UploadSession
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)


class LocalFileStorageAdapter(FileStorageProtocol):
    """Local filesystem implementation of file storage protocol.

    Handles file storage operations using the local filesystem.
    """

    def __init__(self, base_temp_path: str = "temp_uploads"):
        """Initialize local file storage adapter.

        Args:
            base_temp_path: Base path for temporary upload files
        """
        self._base_temp_path = Path(base_temp_path)
        self._base_temp_path.mkdir(parents=True, exist_ok=True)

    async def create_session_directory(self, session_id: str) -> Path:
        """Create directory for upload session.

        Args:
            session_id: Unique session identifier

        Returns:
            Path to created directory
        """
        session_dir = self._base_temp_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"📁 Created session directory: {session_dir}")
        return session_dir

    @handle_errors("store_chunk")
    async def store_chunk(self, session_id: str, chunk: FileChunk) -> None:
        """Store a file chunk.

        Args:
            session_id: Session identifier
            chunk: File chunk to store
        """
        session_dir = self._base_temp_path / session_id
        chunk_file = session_dir / f"chunk_{chunk.index:06d}.dat"

        # Write chunk data to file
        with open(chunk_file, "wb") as f:
            f.write(chunk.data)
        logger.debug(f"💾 Stored chunk {chunk.index} for session {session_id}")

    @handle_errors("assemble_file")
    async def assemble_file(self, session: UploadSession, output_path: Path) -> Path:
        """Assemble chunks into final file.

        Args:
            session: Upload session with chunk information
            output_path: Destination path for assembled file

        Returns:
            Path to assembled file
        """
        session_dir = self._base_temp_path / session.session_id

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Assemble chunks in order
        with open(output_path, "wb") as output_file:
            for chunk_index in range(session.total_chunks):
                chunk_file = session_dir / f"chunk_{chunk_index:06d}.dat"
                if not chunk_file.exists():
                    raise FileNotFoundError(f"Missing chunk file: {chunk_file}")
                with open(chunk_file, "rb") as chunk_f:
                    chunk_data = chunk_f.read()
                    output_file.write(chunk_data)
        # Verify assembled file size
        actual_size = output_path.stat().st_size
        if actual_size != session.total_size_bytes:
            raise ValueError(
                f"Assembled file size ({actual_size}) does not match expected size ({session.total_size_bytes})"
            )
        logger.info(f"🔧 Assembled file: {output_path} ({actual_size:,} bytes)")
        return output_path

    @handle_errors("cleanup_session")
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session temporary files.

        Args:
            session_id: Session to clean up
        """
        session_dir = self._base_temp_path / session_id

        if session_dir.exists():
            shutil.rmtree(session_dir)
            logger.debug(f"🧹 Cleaned up session directory: {session_dir}")

    @handle_errors("get_chunk_info")
    async def get_chunk_info(self, session_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """Get information about a stored chunk.

        Args:
            session_id: Session identifier
            chunk_index: Chunk index

        Returns:
            Chunk info dictionary or None if not found
        """
        session_dir = self._base_temp_path / session_id
        chunk_file = session_dir / f"chunk_{chunk_index:06d}.dat"

        if not chunk_file.exists():
            return None

        stat = chunk_file.stat()
        return {
            "chunk_index": chunk_index,
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "file_path": str(chunk_file),
        }

    async def verify_file_integrity(self, file_path: Path, expected_size: int) -> bool:
        """Verify file integrity after assembly.

        Args:
            file_path: Path to file to verify
            expected_size: Expected file size in bytes

        Returns:
            True if file is valid
        """
        try:
            if not file_path.exists():
                logger.error(f"❌ File does not exist: {file_path}")
                return False

            actual_size = file_path.stat().st_size
            if actual_size != expected_size:
                logger.error(f"❌ Size mismatch: expected {expected_size:,}, got {actual_size:,}",
                )
                return False

            # Additional checks could be added here (checksums, etc.)
            logger.debug(f"✅ File integrity verified: {file_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Error verifying file integrity: {e}")
            return False
