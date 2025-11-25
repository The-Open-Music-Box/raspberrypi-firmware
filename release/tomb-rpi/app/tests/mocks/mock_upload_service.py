# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock UploadService for testing.

This module provides a mock implementation of upload services
for testing file upload workflows without actual file operations.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class MockChunkedUploadService:
    """Mock ChunkedUploadService implementation for testing."""

    def __init__(self):
        """Initialize the mock upload service."""
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._completed_uploads: Dict[str, Dict[str, Any]] = {}

    async def init_session(
        self,
        playlist_id: str,
        filename: str,
        file_size: int,
        chunk_size: int = 1024 * 1024,
        file_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize an upload session.

        Args:
            playlist_id: Target playlist ID
            filename: Name of the file being uploaded
            file_size: Total file size in bytes
            chunk_size: Size of each chunk
            file_hash: Optional file hash for validation

        Returns:
            Session initialization result
        """
        session_id = str(uuid.uuid4())
        total_chunks = (file_size + chunk_size - 1) // chunk_size

        session_data = {
            "session_id": session_id,
            "playlist_id": playlist_id,
            "filename": filename,
            "file_size": file_size,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "chunks_received": 0,
            "chunks_data": {},
            "file_hash": file_hash,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "status": "active",
        }

        self._sessions[session_id] = session_data

        return {
            "status": "success",
            "session_id": session_id,
            "total_chunks": total_chunks,
            "chunk_size": chunk_size,
        }

    async def upload_chunk(
        self, session_id: str, chunk_index: int, chunk_data: bytes
    ) -> Dict[str, Any]:
        """Upload a file chunk.

        Args:
            session_id: Upload session ID
            chunk_index: Index of the chunk being uploaded
            chunk_data: Binary chunk data

        Returns:
            Chunk upload result
        """
        if session_id not in self._sessions:
            return {"status": "error", "message": "Session not found"}

        session = self._sessions[session_id]

        if chunk_index >= session["total_chunks"]:
            return {"status": "error", "message": "Invalid chunk index"}

        if chunk_index in session["chunks_data"]:
            return {"status": "error", "message": "Chunk already uploaded"}

        # Store chunk data (in real implementation would write to disk)
        session["chunks_data"][chunk_index] = len(chunk_data)
        session["chunks_received"] += 1
        session["last_activity"] = datetime.now().isoformat()

        progress = (session["chunks_received"] / session["total_chunks"]) * 100

        return {
            "status": "success",
            "chunks_received": session["chunks_received"],
            "total_chunks": session["total_chunks"],
            "progress_percent": round(progress, 2),
        }

    async def finalize_upload(
        self, session_id: str, file_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finalize an upload session.

        Args:
            session_id: Upload session ID
            file_hash: Optional hash for validation

        Returns:
            Finalization result
        """
        if session_id not in self._sessions:
            return {"status": "error", "message": "Session not found"}

        session = self._sessions[session_id]

        if session["chunks_received"] != session["total_chunks"]:
            return {
                "status": "error",
                "message": f"Incomplete upload: {session['chunks_received']}/{session['total_chunks']} chunks",
            }

        # Simulate successful file assembly
        completed_upload = {
            **session,
            "completed_at": datetime.now().isoformat(),
            "final_file_path": f"/uploads/{session['playlist_id']}/{session['filename']}",
            "status": "completed",
        }

        self._completed_uploads[session_id] = completed_upload
        session["status"] = "completed"

        return {
            "status": "success",
            "file_path": completed_upload["final_file_path"],
            "track": {
                "id": len(self._completed_uploads),
                "filename": session["filename"],
                "title": session["filename"].split(".")[0],
                "duration": 180000,  # 3 minutes in ms
                "file_size": session["file_size"],
            },
        }

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get upload session status.

        Args:
            session_id: Upload session ID

        Returns:
            Session status information
        """
        if session_id not in self._sessions:
            return {"status": "error", "message": "Session not found"}

        session = self._sessions[session_id]
        progress = (session["chunks_received"] / session["total_chunks"]) * 100

        return {
            "status": "success",
            "session_data": {
                "session_id": session_id,
                "filename": session["filename"],
                "file_size": session["file_size"],
                "chunks_received": session["chunks_received"],
                "total_chunks": session["total_chunks"],
                "progress_percent": round(progress, 2),
                "status": session["status"],
                "created_at": session["created_at"],
                "last_activity": session["last_activity"],
            },
        }

    async def cleanup_stale_sessions(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Clean up stale upload sessions.

        Args:
            max_age_hours: Maximum age for sessions in hours

        Returns:
            Cleanup result
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        stale_sessions = []

        for session_id, session in list(self._sessions.items()):
            try:
                session_time = datetime.fromisoformat(session["created_at"].replace("Z", ""))
                if session_time < cutoff_time:
                    stale_sessions.append(
                        {
                            "session_id": session_id,
                            "filename": session["filename"],
                            "age_hours": (datetime.now() - session_time).total_seconds() / 3600,
                        }
                    )
                    del self._sessions[session_id]
            except (ValueError, TypeError):
                # Remove sessions with invalid timestamps
                stale_sessions.append(
                    {
                        "session_id": session_id,
                        "filename": session.get("filename", "unknown"),
                        "age_hours": "invalid_timestamp",
                    }
                )
                del self._sessions[session_id]

        return {
            "status": "success",
            "cleaned_sessions": stale_sessions,
            "count": len(stale_sessions),
        }

    # Mock-specific testing methods
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all upload sessions for testing.

        Returns:
            Dictionary of all sessions
        """
        return self._sessions.copy()

    def get_completed_uploads(self) -> Dict[str, Dict[str, Any]]:
        """Get all completed uploads for testing.

        Returns:
            Dictionary of all completed uploads
        """
        return self._completed_uploads.copy()

    def simulate_partial_upload(
        self, playlist_id: str, filename: str, chunks_uploaded: int, total_chunks: int
    ) -> str:
        """Simulate a partially uploaded file for testing.

        Args:
            playlist_id: Target playlist ID
            filename: Filename
            chunks_uploaded: Number of chunks already uploaded
            total_chunks: Total number of chunks

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "playlist_id": playlist_id,
            "filename": filename,
            "file_size": total_chunks * 1024 * 1024,  # Assume 1MB chunks
            "chunk_size": 1024 * 1024,
            "total_chunks": total_chunks,
            "chunks_received": chunks_uploaded,
            "chunks_data": {i: 1024 * 1024 for i in range(chunks_uploaded)},
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "status": "active",
        }

        self._sessions[session_id] = session_data
        return session_id

    def clear_sessions(self):
        """Clear all sessions for testing."""
        self._sessions.clear()
        self._completed_uploads.clear()

    def reset(self):
        """Reset the mock upload service to initial state."""
        self.clear_sessions()


class MockUploadService:
    """Mock UploadService wrapper for testing."""

    def __init__(self):
        """Initialize the mock upload service."""
        self.chunked = MockChunkedUploadService()

    def reset(self):
        """Reset the mock upload service."""
        self.chunked.reset()
