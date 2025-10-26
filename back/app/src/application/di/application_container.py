# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Application Layer Dependency Injection Container.

This container wires Application services using proper dependency injection
following Clean Architecture principles.
"""

from typing import Dict, Any, Callable, TypeVar
import logging

# Direct imports - no more dynamic imports
from app.src.infrastructure.di.container import get_container as get_infrastructure_container
from app.src.application.services.data_application_service import DataApplicationService
from app.src.application.services.audio_application_service import AudioApplicationService
from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.application.services.upload_application_service import UploadApplicationService
from app.src.domain.audio.engine.state_manager import StateManager
from app.src.infrastructure.nfc.nfc_factory import NfcFactory
from app.src.infrastructure.upload.upload_factory import UploadFactory

T = TypeVar('T')

logger = logging.getLogger(__name__)


class ApplicationContainer:
    """Application Layer DI Container following Clean Architecture."""

    def __init__(self, infrastructure_container):
        """Initialize with reference to infrastructure container.

        Args:
            infrastructure_container: The infrastructure DI container
        """
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._infrastructure_container = infrastructure_container

    def register_singleton(self, service_name: str, instance: Any) -> None:
        """Register a singleton instance."""
        self._singletons[service_name] = instance
        logger.debug(f"Application container registered singleton: {service_name}")

    def register_factory(self, service_name: str, factory: Callable, singleton: bool = True) -> None:
        """Register a factory function.

        Args:
            service_name: Name of the service
            factory: Factory function that creates the service
            singleton: If True, cache the instance after first creation (default: True)
        """
        self._factories[service_name] = factory
        if singleton:
            # Mark this service as needing singleton behavior
            self._services[service_name] = None  # Placeholder to track singleton intent
        logger.debug(f"Application container registered factory: {service_name} (singleton={singleton})")

    def get(self, service_name: str) -> Any:
        """Get a service instance."""
        # Check singletons first
        if service_name in self._singletons:
            return self._singletons[service_name]

        # Check factories
        if service_name in self._factories:
            instance = self._factories[service_name]()
            # Cache as singleton if this service was marked for singleton behavior
            if service_name in self._services:
                self._singletons[service_name] = instance
            return instance

        # Delegate to infrastructure container for infrastructure services
        try:
            return self._infrastructure_container.get(service_name)
        except KeyError:
            raise KeyError(f"Service '{service_name}' not found in application or infrastructure containers")


# Global application container instance
_application_container = None


def get_application_container() -> ApplicationContainer:
    """Get the global application container."""
    global _application_container
    if _application_container is None:
        infrastructure_container = get_infrastructure_container()
        _application_container = ApplicationContainer(infrastructure_container)
        register_application_services(_application_container)
    return _application_container


def register_application_services(container: ApplicationContainer) -> None:
    """Register Application layer services."""

    # Register Application Services
    def data_application_service_factory():
        playlist_service = container.get("data_playlist_service")
        track_service = container.get("data_track_service")
        return DataApplicationService(playlist_service=playlist_service, track_service=track_service)
    container.register_factory("data_application_service", data_application_service_factory)

    def audio_application_service_factory():
        # Get audio domain container from infrastructure DI
        infra_container = get_infrastructure_container()
        audio_domain_container = infra_container.get("audio_domain_container")

        # Initialize audio domain container if needed
        if not audio_domain_container.is_initialized:
            domain_bootstrap = infra_container.get("domain_bootstrap")
            if not domain_bootstrap.is_initialized:
                domain_bootstrap.initialize()

        playlist_service = container.get("data_application_service")
        return AudioApplicationService(
            audio_domain_container=audio_domain_container,
            playlist_application_service=playlist_service,
            state_manager=StateManager(),
        )
    container.register_factory("audio_application_service", audio_application_service_factory)

    def nfc_application_service_factory():
        hardware, repository, nfc_association_service = NfcFactory.create_nfc_infrastructure_components()
        return NfcApplicationService(
            nfc_hardware=hardware,
            nfc_repository=repository,
            nfc_association_service=nfc_association_service,
        )
    container.register_factory("nfc_application_service", nfc_application_service_factory)

    def upload_application_service_factory():
        file_storage, metadata_extractor, validation_service, upload_folder = UploadFactory.create_upload_infrastructure_components()
        return UploadApplicationService(
            file_storage=file_storage,
            metadata_extractor=metadata_extractor,
            validation_service=validation_service,
            upload_folder=upload_folder,
        )
    container.register_factory("upload_application_service", upload_application_service_factory)

    def playback_coordinator_factory():
        # Create playback coordinator directly to avoid circular import
        from app.src.application.controllers.playback_coordinator_controller import PlaybackCoordinator
        from app.src.infrastructure.di.container import get_container

        # Get dependencies from DI container
        infra_container = get_container()
        domain_bootstrap = infra_container.get("domain_bootstrap")
        audio_domain_container = infra_container.get("audio_domain_container")

        # Initialize domain if not already done
        if not domain_bootstrap.is_initialized:
            domain_bootstrap.initialize()

        # Get domain playlist service via DI
        playlist_service = container.get("data_playlist_service")

        # Get data application service for NFC lookups
        data_app_service = container.get("data_application_service")

        # Get audio backend from domain container
        if audio_domain_container.is_initialized:
            audio_backend = audio_domain_container.backend
            return PlaybackCoordinator(
                audio_backend,
                playlist_service=playlist_service,
                socketio=None,
                data_application_service=data_app_service
            )

        # Fallback: create with mock backend
        from app.src.domain.audio.backends.implementations.mock_audio_backend import MockAudioBackend
        return PlaybackCoordinator(
            MockAudioBackend(),
            playlist_service=playlist_service,
            socketio=None,
            data_application_service=data_app_service
        )
    container.register_factory("playback_coordinator", playback_coordinator_factory)

    logger.info("✅ Application services registered in Application DI container")
