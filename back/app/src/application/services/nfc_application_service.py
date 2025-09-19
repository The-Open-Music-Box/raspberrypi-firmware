# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Application Service - Use Cases Orchestration."""

import asyncio
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING

from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.domain.nfc.services.nfc_association_service import NfcAssociationService
from app.src.domain.nfc.protocols.nfc_hardware_protocol import (
    NfcHardwareProtocol,
    NfcRepositoryProtocol,
)
from app.src.monitoring import get_logger
from app.src.monitoring.logging.log_level import LogLevel

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from app.src.domain.repositories.playlist_repository_interface import PlaylistRepositoryProtocol
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class NfcApplicationService:
    """Application service orchestrating NFC use cases.

    Coordinates between domain services, hardware adapters, and external
    systems to implement complete NFC-related use cases.
    """

    def __init__(
        self,
        nfc_hardware: NfcHardwareProtocol,
        nfc_repository: NfcRepositoryProtocol,
        nfc_association_service: Optional[NfcAssociationService] = None,
        playlist_repository: Optional["PlaylistRepositoryProtocol"] = None,
    ):
        """Initialize NFC application service.

        Args:
            nfc_hardware: Hardware adapter for NFC operations
            nfc_repository: Repository for NFC persistence
            nfc_association_service: Domain service for associations
            playlist_repository: Repository for playlist sync (optional)
        """
        self._nfc_hardware = nfc_hardware
        self._nfc_repository = nfc_repository

        # Pass playlist repository to domain service for synchronization
        self._association_service = nfc_association_service or NfcAssociationService(
            nfc_repository, playlist_repository
        )

        # Event callbacks
        self._tag_detected_callbacks: List[Callable[[str], None]] = []
        self._association_callbacks: List[Callable[[Dict], None]] = []

        # Setup hardware callbacks
        self._nfc_hardware.set_tag_detected_callback(self._on_tag_detected)
        self._nfc_hardware.set_tag_removed_callback(self._on_tag_removed)

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    @handle_service_errors("nfc_application")
    async def start_nfc_system(self) -> Dict[str, Any]:
        """Start the NFC system.

        Returns:
            Status dictionary
        """
        await self._nfc_hardware.start_detection()
        # Start cleanup task for expired sessions
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.log(LogLevel.INFO, "✅ NFC system started successfully")
        return {
            "status": "success",
            "message": "NFC system started",
            "hardware_status": self._nfc_hardware.get_hardware_status(),
        }

    @handle_service_errors("nfc_application")
    async def stop_nfc_system(self) -> Dict[str, Any]:
        """Stop the NFC system.

        Returns:
            Status dictionary
        """
        await self._nfc_hardware.stop_detection()
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling

        logger.log(LogLevel.INFO, "✅ NFC system stopped successfully")
        return {"status": "success", "message": "NFC system stopped"}

    @handle_service_errors("nfc_application")
    async def start_association_use_case(
        self, playlist_id: str, timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """Use case: Start associating a playlist with an NFC tag.

        Args:
            playlist_id: ID of playlist to associate
            timeout_seconds: Association timeout

        Returns:
            Result dictionary with session info
        """
        session = await self._association_service.start_association_session(
            playlist_id, timeout_seconds
        )
        return {
            "status": "success",
            "message": "Association session started",
            "session": session.to_dict(),
        }

    @handle_service_errors("nfc_application")
    async def stop_association_use_case(self, session_id: str) -> Dict[str, Any]:
        """Use case: Stop an association session.

        Args:
            session_id: ID of session to stop

        Returns:
            Result dictionary
        """
        success = await self._association_service.stop_association_session(session_id)
        if success:
            return {
                "status": "success",
                "message": "Association session stopped",
                "session_id": session_id,
            }
        else:
            return {
                "status": "error",
                "message": "Association session not found",
                "error_type": "not_found",
            }

    @handle_service_errors("nfc_application")
    async def get_nfc_status_use_case(self) -> Dict[str, Any]:
        """Use case: Get comprehensive NFC system status.

        Returns:
            Status dictionary with all NFC information
        """
        hardware_status = (
            self._nfc_hardware.get_hardware_status()
        )  # Removed await - it's synchronous
        active_sessions = self._association_service.get_active_sessions()
        return {
            "status": "success",
            "hardware": hardware_status,
            "detecting": self._nfc_hardware.is_detecting(),
            "active_sessions": [session.to_dict() for session in active_sessions],
            "session_count": len(active_sessions),
        }

    @handle_service_errors("nfc_application")
    async def dissociate_tag_use_case(self, tag_id: str) -> Dict[str, Any]:
        """Use case: Dissociate a tag from its playlist.

        Args:
            tag_id: Tag identifier to dissociate

        Returns:
            Result dictionary
        """
        tag_identifier = TagIdentifier(uid=tag_id)
        success = await self._association_service.dissociate_tag(tag_identifier)
        if success:
            return {
                "status": "success",
                "message": f"Tag {tag_id} dissociated successfully",
                "tag_id": tag_id,
            }
        else:
            return {"status": "error", "message": "Tag not found", "error_type": "not_found"}

    def register_tag_detected_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for tag detection events.

        Args:
            callback: Function to call when tag is detected
        """
        self._tag_detected_callbacks.append(callback)

    def register_association_callback(self, callback: Callable[[Dict], None]) -> None:
        """Register callback for association events.

        Args:
            callback: Function to call when association events occur
        """
        self._association_callbacks.append(callback)

    @handle_service_errors("nfc_application")
    def _on_tag_detected(self, tag_data) -> None:
        """Handle tag detection from hardware."""
        # Convert string or dict to TagIdentifier
        if isinstance(tag_data, str):
            tag_identifier = TagIdentifier(uid=tag_data)
        elif isinstance(tag_data, dict) and "uid" in tag_data:
            tag_identifier = TagIdentifier(uid=tag_data["uid"])
        elif hasattr(tag_data, "uid"):
            tag_identifier = tag_data  # Already a TagIdentifier
        else:
            logger.log(LogLevel.ERROR, f"❌ Unknown tag data format: {tag_data}")
            return
        logger.log(LogLevel.DEBUG, f"🔄 NfcApplicationService received tag: {tag_identifier}")
        asyncio.create_task(self._handle_tag_detection(tag_identifier))

    def _on_tag_removed(self) -> None:
        """Handle tag removal from hardware."""
        logger.log(LogLevel.DEBUG, "📱 NFC tag removed")

    @handle_service_errors("nfc_application")
    async def _handle_tag_detection(self, tag_identifier: TagIdentifier) -> None:
        """Handle detected tag processing."""
        logger.log(
            LogLevel.INFO, f"🔄 NfcApplicationService processing tag detection: {tag_identifier}"
        )
        # Process through association service
        result = await self._association_service.process_tag_detection(tag_identifier)
        # Notify callbacks
        logger.log(
            LogLevel.DEBUG,
            f"🔔 Notifying {len(self._tag_detected_callbacks)} tag detection callbacks",
        )
        for callback in self._tag_detected_callbacks:
            callback(str(tag_identifier))

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired sessions."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                cleaned = await self._association_service.cleanup_expired_sessions()
                if cleaned > 0:
                    logger.log(LogLevel.INFO, f"🧹 Cleaned up {cleaned} expired NFC sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.log(LogLevel.WARNING, f"⚠️ Error in NFC cleanup: {e}")
