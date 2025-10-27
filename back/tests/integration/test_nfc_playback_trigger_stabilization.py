# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Integration tests for NFC playback trigger stabilization.

Tests the complete fix for multiple playlist triggers issue:
1. Tag absence events don't trigger playback
2. Same tag held on reader doesn't re-trigger
3. Tag removal then re-insertion allows new trigger
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService
from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.infrastructure.nfc.repositories.nfc_memory_repository import NfcMemoryRepository
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier


class MockNfcHardware:
    """Mock NFC hardware that simulates real hardware behavior."""

    def __init__(self):
        self._tag_detected_callback = None
        self._tag_removed_callback = None
        self._detecting = False

    def set_tag_detected_callback(self, callback):
        """Set tag detected callback."""
        self._tag_detected_callback = callback

    def set_tag_removed_callback(self, callback):
        """Set tag removed callback."""
        self._tag_removed_callback = callback

    async def start_detection(self):
        """Start detection."""
        self._detecting = True

    async def stop_detection(self):
        """Stop detection."""
        self._detecting = False

    def is_detecting(self):
        """Check if detecting."""
        return self._detecting

    def get_hardware_status(self):
        """Get hardware status."""
        return {
            "available": True,
            "detecting": self._detecting,
            "hardware_type": "mock"
        }

    def simulate_tag_present(self, tag_uid: str):
        """Simulate tag presence (tag_present event)."""
        if self._tag_detected_callback:
            tag_data = {
                "uid": tag_uid,
                "present": True,
                "timestamp": asyncio.get_event_loop().time()
            }
            self._tag_detected_callback(tag_data)

    def simulate_tag_absent(self, tag_uid: str):
        """Simulate tag absence (tag_absent event)."""
        if self._tag_removed_callback:
            # This should trigger tag_removed_callback, NOT tag_detected_callback
            tag_data = {
                "uid": tag_uid,
                "present": False,
                "absence": True,
                "timestamp": asyncio.get_event_loop().time()
            }
            # The hardware adapter should call tag_removed_callback when it sees "absence": True
            self._tag_removed_callback()


@pytest.mark.asyncio
class TestNfcPlaybackTriggerStabilization:
    """Integration tests for NFC playback trigger stabilization."""

    @pytest.fixture
    async def playlist_repo(self):
        """Get playlist repository instance."""
        return PureSQLitePlaylistRepository()

    @pytest.fixture
    async def track_service(self, playlist_repo):
        """Get track service instance."""
        return TrackService(playlist_repo, playlist_repo)

    @pytest.fixture
    async def playlist_service(self, playlist_repo, track_service):
        """Get playlist service instance."""
        return PlaylistService(playlist_repo, track_service._track_repo)

    @pytest.fixture
    async def nfc_hardware(self):
        """Get mock NFC hardware."""
        return MockNfcHardware()

    @pytest.fixture
    async def nfc_app_service(self, nfc_hardware, playlist_repo):
        """Get NFC application service."""
        nfc_repository = NfcMemoryRepository()
        service = NfcApplicationService(
            nfc_hardware=nfc_hardware,
            nfc_repository=nfc_repository,
            playlist_repository=playlist_repo
        )
        await service.start_nfc_system()
        return service

    async def test_scenario_1_first_scan_triggers_once(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware
    ):
        """
        SCENARIO 1: Premier scan - La playlist se lance UNE seule fois.

        Issue originale: La playlist se lançait deux fois au premier scan.
        """
        # Setup
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]

        playlist = Playlist(
            id=playlist_id,
            title="Test Playlist",
            nfc_tag_id=test_nfc_tag,
            tracks=[]
        )
        await playlist_repo.save(playlist)

        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        try:
            # Act - Premier scan du tag
            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.2)

            # Assert - Playback déclenché UNE SEULE fois
            assert playback_count == 1, f"Expected 1 playback trigger, got {playback_count}"

        finally:
            await playlist_repo.delete(playlist_id)
            await nfc_app_service.stop_nfc_system()

    async def test_scenario_2_tag_held_no_retrigger(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware
    ):
        """
        SCENARIO 2: Tag maintenu - Pas de redémarrage automatique.

        Issue originale: Si l'utilisateur arrête la playlist avec le tag
        toujours présent, elle se relançait automatiquement.
        """
        # Setup
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]

        playlist = Playlist(
            id=playlist_id,
            title="Test Playlist",
            nfc_tag_id=test_nfc_tag,
            tracks=[]
        )
        await playlist_repo.save(playlist)

        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        try:
            # Act - Tag détecté
            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.2)

            # Utilisateur "arrête" la playlist (simule pause/stop)
            # Tag toujours présent

            # Nouvelles détections du même tag (hardware scan loop)
            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.1)

            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.1)

            # Assert - Playback ne se relance PAS
            assert playback_count == 1, f"Expected 1 playback trigger, got {playback_count}"

        finally:
            await playlist_repo.delete(playlist_id)
            await nfc_app_service.stop_nfc_system()

    async def test_scenario_3_tag_removal_no_trigger(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware
    ):
        """
        SCENARIO 3: Retrait du tag - PAS de déclenchement.

        Issue originale: Retirer le tag était considéré comme un trigger
        et relançait la playlist.
        """
        # Setup
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]

        playlist = Playlist(
            id=playlist_id,
            title="Test Playlist",
            nfc_tag_id=test_nfc_tag,
            tracks=[]
        )
        await playlist_repo.save(playlist)

        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        try:
            # Act - Tag détecté puis retiré
            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.2)

            initial_count = playback_count

            # Retrait du tag (CRITICAL FIX: doit appeler tag_removed_callback)
            nfc_hardware.simulate_tag_absent(test_nfc_tag)
            await asyncio.sleep(0.2)

            # Assert - Le retrait ne déclenche PAS de playback
            assert playback_count == initial_count, \
                f"Tag removal should NOT trigger playback (was {initial_count}, now {playback_count})"

        finally:
            await playlist_repo.delete(playlist_id)
            await nfc_app_service.stop_nfc_system()

    async def test_scenario_4_tag_reinsertion_allows_retrigger(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware
    ):
        """
        SCENARIO 4: Retrait puis réinsertion - Nouveau trigger autorisé.

        Comportement attendu: Retirer puis remettre le tag DOIT permettre
        un nouveau déclenchement de la playlist.
        """
        # Setup
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]

        playlist = Playlist(
            id=playlist_id,
            title="Test Playlist",
            nfc_tag_id=test_nfc_tag,
            tracks=[]
        )
        await playlist_repo.save(playlist)

        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        try:
            # Act - Cycle complet: Détection → Retrait → Réinsertion
            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.2)

            nfc_hardware.simulate_tag_absent(test_nfc_tag)
            await asyncio.sleep(0.2)

            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.2)

            # Assert - Deux triggers (un par insertion)
            assert playback_count == 2, \
                f"Expected 2 playback triggers (one per insertion), got {playback_count}"

        finally:
            await playlist_repo.delete(playlist_id)
            await nfc_app_service.stop_nfc_system()

    async def test_scenario_5_association_workflow_unaffected(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware
    ):
        """
        SCENARIO 5: Workflow d'association - Non affecté par les changements.

        Vérifier que l'association NFC fonctionne toujours correctement.
        """
        # Setup
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]

        playlist = Playlist(
            id=playlist_id,
            title="Test Playlist",
            nfc_tag_id=None,  # Pas encore associé
            tracks=[]
        )
        await playlist_repo.save(playlist)

        playback_count = 0
        association_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        def association_callback(result: dict):
            nonlocal association_count
            if result.get("action") == "association_success":
                association_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)
        nfc_app_service.register_association_callback(association_callback)

        try:
            # Act - Démarrer session d'association
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            assert session_result["status"] == "success"

            # Scanner tag pendant l'association
            nfc_hardware.simulate_tag_present(test_nfc_tag)
            await asyncio.sleep(0.3)

            # Assert - Association réussie, MAIS pas de playback pendant association
            assert association_count >= 1, "Association should have succeeded"
            assert playback_count == 0, "Playback should NOT trigger during association"

            # Vérifier que le tag est bien associé dans la DB
            updated_playlist = await playlist_repo.find_by_id(playlist_id)
            assert updated_playlist.nfc_tag_id == test_nfc_tag

        finally:
            await playlist_repo.delete(playlist_id)
            await nfc_app_service.stop_nfc_system()
