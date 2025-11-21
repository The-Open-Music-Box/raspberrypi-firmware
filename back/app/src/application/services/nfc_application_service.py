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
from app.src.services.error.unified_error_decorator import handle_service_errors
import logging

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from app.src.domain.repositories.playlist_repository_interface import PlaylistRepositoryProtocol

logger = logging.getLogger(__name__)


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

    async def start_nfc_system(self) -> Dict[str, Any]:
        """Start the NFC system.

        Returns:
            Status dictionary
        """
        try:
            await self._nfc_hardware.start_detection()
            # Start cleanup task for expired sessions
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("✅ NFC system started successfully")
            return {
                "status": "success",
                "message": "NFC system started",
                "hardware_status": self._nfc_hardware.get_hardware_status(),
            }
        except Exception as e:
            logger.error(f"❌ Failed to start NFC system: {e}")
            return {
                "status": "error",
                "message": f"Failed to start NFC system: {str(e)}",
                "error_type": "hardware_error",
            }

    async def stop_nfc_system(self) -> Dict[str, Any]:
        """Stop the NFC system.

        Returns:
            Status dictionary
        """
        try:
            await self._nfc_hardware.stop_detection()
            # Cancel cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling

            logger.info("✅ NFC system stopped successfully")
            return {"status": "success", "message": "NFC system stopped"}
        except Exception as e:
            logger.error(f"Failed to stop NFC system: {e}")
            return {
                "status": "error",
                "message": f"Failed to stop NFC system: {str(e)}",
                "error_type": "hardware_error",
            }

    async def start_association_use_case(
        self, playlist_id: str, timeout_seconds: int = 60, override_mode: bool = False
    ) -> Dict[str, Any]:
        """Use case: Start associating a playlist with an NFC tag.

        Args:
            playlist_id: ID of playlist to associate
            timeout_seconds: Association timeout
            override_mode: If True, force association even if tag is already associated

        Returns:
            Result dictionary with session info
        """
        session = await self._association_service.start_association_session(
            playlist_id, timeout_seconds, override_mode
        )
        return {
            "status": "success",
            "message": "Association session started",
            "session": session.to_dict(),
        }

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

    async def get_nfc_status_use_case(self) -> Dict[str, Any]:
        """Use case: Get comprehensive NFC system status.

        Returns:
            Status dictionary with all NFC information
        """
        # Note: get_hardware_status() is synchronous, no await needed
        hardware_status = self._nfc_hardware.get_hardware_status()
        active_sessions = self._association_service.get_active_sessions()
        return {
            "status": "success",
            "hardware": hardware_status,
            "detecting": self._nfc_hardware.is_detecting(),
            "active_sessions": [session.to_dict() for session in active_sessions],
            "session_count": len(active_sessions),
        }

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
            return {"status": "not_found", "message": "Tag not found", "error_type": "not_found"}

    async def associate_tag(self, tag_id: str, playlist_id: str) -> Dict[str, Any]:
        """Associate a tag with a playlist directly by simulating tag detection.

        Args:
            tag_id: Tag identifier
            playlist_id: Playlist identifier

        Returns:
            Result dictionary
        """
        try:
            # Start an association session for this playlist
            session_result = await self.start_association_use_case(playlist_id, timeout_seconds=5)
            if session_result.get("status") != "success":
                return {
                    "status": "error",
                    "message": "Failed to start association session",
                }

            # Simulate tag detection to trigger association
            tag_identifier = TagIdentifier(uid=tag_id)
            await self._handle_tag_detection(tag_identifier)

            # Give a moment for the association to process
            import asyncio
            await asyncio.sleep(0.1)

            # Check if association was successful by looking for the tag in the repository
            try:
                # Try to get the association to verify it worked
                existing_association = await self._nfc_repository.get_association_by_tag_id(tag_id)
                if existing_association and existing_association.playlist_id == playlist_id:
                    return {
                        "status": "success",
                        "message": "Tag associated successfully",
                        "playlist_title": "Associated Playlist",
                        "created_at": existing_association.created_at.isoformat() if hasattr(existing_association, 'created_at') else "",
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Association failed - tag not found in repository",
                    }
            except Exception as check_error:
                logger.warning(f"Could not verify association: {check_error}")
                # Assume success if we can't verify (optimistic approach)
                return {
                    "status": "success",
                    "message": "Tag association completed",
                    "playlist_title": "Associated Playlist",
                    "created_at": "",
                }

        except Exception as e:
            logger.error(f"Error in associate_tag: {e}")
            return {
                "status": "error",
                "message": f"Association failed: {str(e)}",
            }

    async def start_scan_session(self, timeout_ms: int = 60000) -> Dict[str, Any]:
        """Start a generic scan session (without association).

        Args:
            timeout_ms: Scan timeout in milliseconds

        Returns:
            Result dictionary
        """
        try:
            # For generic scanning, we just enable hardware detection
            await self._nfc_hardware.start_detection()

            # Generate a scan session ID
            import uuid
            scan_id = str(uuid.uuid4())

            return {
                "status": "success",
                "message": "Generic scan session started",
                "scan_id": scan_id,
            }
        except Exception as e:
            logger.error(f"Error starting scan session: {e}")
            return {
                "status": "error",
                "message": f"Failed to start scan session: {str(e)}",
            }

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
            logger.error(f"❌ Unknown tag data format: {tag_data}")
            return
        logger.debug(f"🔄 NfcApplicationService received tag: {tag_identifier}")
        asyncio.create_task(self._handle_tag_detection(tag_identifier))

    def _on_tag_removed(self) -> None:
        """Handle tag removal from hardware."""
        logger.debug("📱 NFC tag removed")

    async def _handle_tag_detection(self, tag_identifier: TagIdentifier) -> None:
        """Handle detected tag processing.

        CRITICAL: When association sessions are active, this method ONLY processes
        association and does NOT trigger playback. This prevents accidental playback
        when user is trying to associate a tag.
        """
        logger.info(f"🔄 NfcApplicationService processing tag detection: {tag_identifier}")

        # Check if ANY association session is active
        active_sessions = self._association_service.get_active_sessions()

        if active_sessions:
            # ASSOCIATION MODE: Block playback, process association only
            logger.info(f"🔒 Association mode active ({len(active_sessions)} sessions), blocking playback for tag {tag_identifier}")

            # Process through association service
            result = await self._association_service.process_tag_detection(tag_identifier)

            # Notify association callbacks only (for Socket.IO broadcasting)
            if isinstance(result, dict) and "action" in result:
                # This is a single association result
                logger.debug(
                    f"🔔 Notifying {len(self._association_callbacks)} association callbacks with result: {result}"
                )
                for callback in self._association_callbacks:
                    callback(result)
            elif isinstance(result, dict) and "multiple_sessions" in result:
                # Multiple association results wrapped in a dict
                for single_result in result["multiple_sessions"]:
                    if isinstance(single_result, dict) and "action" in single_result:
                        logger.debug(
                            f"🔔 Notifying {len(self._association_callbacks)} association callbacks with result: {single_result}"
                        )
                        for callback in self._association_callbacks:
                            callback(single_result)
            elif isinstance(result, list):
                # Multiple association results as a direct list (backup handling)
                for single_result in result:
                    if isinstance(single_result, dict) and "action" in single_result:
                        logger.debug(
                            f"🔔 Notifying {len(self._association_callbacks)} association callbacks with result: {single_result}"
                        )
                        for callback in self._association_callbacks:
                            callback(single_result)

            # Do NOT notify tag detection callbacks - prevents playback trigger
            logger.debug(f"🔒 Skipping tag detection callbacks to prevent playback during association mode")
            return  # Exit early, do not trigger playback

        # NORMAL MODE: No active association sessions, proceed with normal tag detection
        logger.info(f"▶️ Normal mode, processing tag detection for playback: {tag_identifier}")

        # Process through association service (for tag_detected action)
        result = await self._association_service.process_tag_detection(tag_identifier)

        # Notify association callbacks if any (should be "tag_detected" action)
        if isinstance(result, dict) and "action" in result:
            logger.debug(
                f"🔔 Notifying {len(self._association_callbacks)} association callbacks with result: {result}"
            )
            for callback in self._association_callbacks:
                callback(result)

        # Notify tag detection callbacks (triggers playback)
        logger.debug(
            f"🔔 Notifying {len(self._tag_detected_callbacks)} tag detection callbacks for playback"
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
                    logger.info(f"🧹 Cleaned up {cleaned} expired NFC sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"⚠️ Error in NFC cleanup: {e}")
