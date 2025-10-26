# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Association Domain Service."""

from typing import Optional, Dict, List
from datetime import datetime, timezone

from ..entities.nfc_tag import NfcTag
from ..entities.association_session import AssociationSession, SessionState
from ..value_objects.tag_identifier import TagIdentifier
from ..protocols.nfc_hardware_protocol import NfcRepositoryProtocol
import logging

from typing import Any
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_service_errors

logger = logging.getLogger(__name__)


class NfcAssociationService:
    """Domain service for NFC tag association business logic.

    Handles the core business rules for associating NFC tags with playlists,
    managing association sessions, and enforcing business constraints.
    """

    def __init__(
        self,
        nfc_repository: NfcRepositoryProtocol,
        playlist_repository: Optional[Any] = None,
    ):
        """Initialize the association service.

        Args:
            nfc_repository: Repository for NFC tag persistence
            playlist_repository: Repository for playlist sync (optional)
        """
        self._nfc_repository = nfc_repository
        self._playlist_repository = playlist_repository
        self._active_sessions: Dict[str, AssociationSession] = {}

    async def start_association_session(
        self, playlist_id: str, timeout_seconds: int = 60, override_mode: bool = False
    ) -> AssociationSession:
        """Start a new association session for a playlist.

        Args:
            playlist_id: ID of playlist to associate with tag
            timeout_seconds: Session timeout in seconds
            override_mode: If True, force association even if tag is already associated

        Returns:
            New association session

        Raises:
            ValueError: If playlist_id is invalid or session already exists
        """
        if not playlist_id:
            raise ValueError("Playlist ID is required")

        # Check if there's already an active session for this playlist
        existing_session = self._find_active_session_for_playlist(playlist_id)
        if existing_session and not override_mode:
            raise ValueError(f"Association session already active for playlist {playlist_id}")

        # If override mode and existing session exists, stop it first
        if existing_session and override_mode:
            await self.stop_association_session(existing_session.session_id)
            logger.info(f"🔄 Stopped existing session {existing_session.session_id} for override mode")

        # Create new session
        session = AssociationSession(
            playlist_id=playlist_id,
            timeout_seconds=timeout_seconds,
            override_mode=override_mode
        )

        self._active_sessions[session.session_id] = session

        logger.info(
            f"✅ Started association session {session.session_id} for playlist {playlist_id} (override={override_mode})"
        )
        return session

    async def process_tag_detection(
        self, tag_identifier: TagIdentifier, session_id: Optional[str] = None
    ) -> Dict[str, any]:
        """Process a detected NFC tag.

        Args:
            tag_identifier: Detected tag identifier
            session_id: Optional specific session to process for

        Returns:
            Dictionary with processing result
        """
        # Find or create tag
        tag = await self._nfc_repository.find_by_identifier(tag_identifier)
        if not tag:
            tag = NfcTag(identifier=tag_identifier)

        tag.mark_detected()

        # If specific session provided, process only that session
        if session_id:
            session = self._active_sessions.get(session_id)
            if session and session.is_active():
                return await self._process_tag_for_session(tag, session)

        # Otherwise, process for all active sessions
        results = []
        for session in list(self._active_sessions.values()):
            if session.is_active():
                result = await self._process_tag_for_session(tag, session)
                results.append(result)

        # If no active sessions, just save the tag detection
        if not results:
            await self._nfc_repository.save_tag(tag)
            return {
                "action": "tag_detected",
                "tag_id": str(tag_identifier),
                "associated_playlist": tag.get_associated_playlist_id(),
                "no_active_sessions": True,
            }

        return results[0] if len(results) == 1 else {"multiple_sessions": results}

    async def _process_tag_for_session(
        self, tag: NfcTag, session: AssociationSession
    ) -> Dict[str, any]:
        """Process a tag detection for a specific session.

        DATABASE-FIRST ARCHITECTURE:
        The database is the SINGLE SOURCE OF TRUTH (SSOT) for NFC associations.
        We ALWAYS check the database first before any association operation.

        Args:
            tag: Detected NFC tag
            session: Association session to process for

        Returns:
            Processing result dictionary
        """
        session.detect_tag(tag.identifier)

        # ✅ STEP 1: Check DATABASE first (SSOT - Single Source of Truth)
        # The database is the authoritative source, especially after restarts
        existing_playlist_id = None
        if self._playlist_repository:
            existing_playlist = await self._playlist_repository.find_by_nfc_tag(
                str(tag.identifier)
            )
            if existing_playlist:
                existing_playlist_id = existing_playlist.id
                logger.info(
                    f"🔍 Database check: Tag {tag.identifier} found associated with playlist {existing_playlist_id}"
                )

        # ✅ STEP 2: Also check memory cache (for in-session consistency)
        # Memory is checked AFTER database to ensure we have the complete picture
        if not existing_playlist_id and tag.is_associated():
            existing_playlist_id = tag.get_associated_playlist_id()
            logger.info(
                f"🔍 Memory check: Tag {tag.identifier} found in cache with playlist {existing_playlist_id}"
            )

        # ✅ STEP 3: If tag is associated anywhere, handle duplicate detection
        if existing_playlist_id:
            is_same_playlist = existing_playlist_id == session.playlist_id

            # If override mode, force the association regardless
            if session.override_mode:
                logger.warning(
                    f"⚠️ Override mode: Replacing association {tag.identifier}: {existing_playlist_id} -> {session.playlist_id}"
                )
                # Dissociate from old playlist and continue with new association
                tag.dissociate_from_playlist()
                # Continue to association below
            else:
                # Normal mode: return duplicate error (even if same playlist)
                # Only mark as duplicate if session is still in LISTENING state
                # (prevents error when tag is detected multiple times)
                if session.state == SessionState.LISTENING:
                    session.mark_duplicate(existing_playlist_id)
                    logger.warning(
                        f"🔄 Tag {tag.identifier} already associated with playlist {existing_playlist_id} (same={is_same_playlist})"
                    )
                else:
                    logger.debug(
                        f"🔄 Tag {tag.identifier} re-detected, session already in {session.state} state"
                    )

                return {
                    "action": "duplicate_association",
                    "session_id": session.session_id,
                    "playlist_id": session.playlist_id,
                    "tag_id": str(tag.identifier),
                    "existing_playlist_id": existing_playlist_id,
                    "is_same_playlist": is_same_playlist,
                    "session_state": session.state.value,
                }

        # ✅ STEP 4: No existing association found, proceed with new association
        # Update memory cache
        tag.associate_with_playlist(session.playlist_id)
        session.mark_successful()

        # Save to memory repository (cache)
        await self._nfc_repository.save_tag(tag)

        # ✅ STEP 5: Synchronize with database (SSOT)
        # This is CRITICAL - database is the authoritative source
        if self._playlist_repository:
            sync_success = await self._playlist_repository.update_nfc_tag_association(
                session.playlist_id, str(tag.identifier)
            )
            if sync_success:
                logger.info(
                    f"🔄 NFC-Playlist sync successful for tag {tag.identifier} -> playlist {session.playlist_id}"
                )
            else:
                logger.warning(f"⚠️ NFC-Playlist sync failed for tag {tag.identifier}")
        else:
            logger.warning(
                f"⚠️ Playlist repository not available, association saved to memory only (will be lost on restart!)"
            )

        logger.info(
            f"✅ Successfully associated tag {tag.identifier} with playlist {session.playlist_id}"
        )

        # Remove successful session from active sessions after a short delay
        # This allows the UI to see the SUCCESS state briefly before cleanup
        import asyncio

        asyncio.create_task(self._cleanup_successful_session(session.session_id))

        return {
            "action": "association_success",
            "session_id": session.session_id,
            "playlist_id": session.playlist_id,
            "tag_id": str(tag.identifier),
            "session_state": session.state.value,
        }

    async def stop_association_session(self, session_id: str) -> bool:
        """Stop an association session.

        Args:
            session_id: ID of session to stop

        Returns:
            True if session was stopped, False if not found
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return False

        session.mark_cancelled()  # Mark as cancelled instead of stopped
        logger.info(f"🛑 Cancelled association session {session_id}")
        return True

    async def get_association_session(self, session_id: str) -> Optional[AssociationSession]:
        """Get an association session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Association session if found, None otherwise
        """
        return self._active_sessions.get(session_id)

    def get_active_sessions(self) -> List[AssociationSession]:
        """Get all active association sessions.

        Returns:
            List of active sessions
        """
        return [session for session in self._active_sessions.values() if session.is_active()]

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired association sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_count = 0
        expired_sessions = []

        for session_id, session in self._active_sessions.items():
            if session.is_expired() and session.state == SessionState.LISTENING:
                session.mark_timeout()
                expired_sessions.append(session_id)
                expired_count += 1

        for session_id in expired_sessions:
            logger.info(f"🕒 Association session {session_id} timed out")

        return expired_count

    def _find_active_session_for_playlist(self, playlist_id: str) -> Optional[AssociationSession]:
        """Find active session for a playlist.

        Args:
            playlist_id: Playlist ID to search for

        Returns:
            Active session if found, None otherwise
        """
        for session in self._active_sessions.values():
            if session.playlist_id == playlist_id and session.is_active():
                return session
        return None

    async def dissociate_tag(self, tag_identifier: TagIdentifier) -> bool:
        """Dissociate a tag from its playlist.

        Args:
            tag_identifier: Tag to dissociate

        Returns:
            True if dissociated, False if tag not found
        """
        tag = await self._nfc_repository.find_by_identifier(tag_identifier)
        if not tag:
            return False

        old_playlist_id = tag.get_associated_playlist_id()
        tag.dissociate_from_playlist()
        await self._nfc_repository.save_tag(tag)

        logger.info(f"✅ Dissociated tag {tag_identifier} from playlist {old_playlist_id}")
        return True

    async def _cleanup_successful_session(self, session_id: str) -> None:
        """Clean up a successful association session after a short delay.

        Args:
            session_id: ID of session to clean up
        """
        import asyncio

        # Wait 2 seconds to allow UI to show success state
        await asyncio.sleep(2.0)

        session = self._active_sessions.get(session_id)
        if session and session.state == SessionState.SUCCESS:
            # Remove from active sessions
            del self._active_sessions[session_id]
            logger.info(f"🧹 Cleaned up successful association session {session_id}")
        elif session:
            logger.debug(f"Session {session_id} not cleaned up - state: {session.state}")
        else:
            logger.debug(f"Session {session_id} not found for cleanup")
