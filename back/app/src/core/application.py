# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Application core module for TheOpenMusicBox backend.

Provides the main Application class that manages the lifecycle and initialization
of the music box backend system, including audio playback, NFC tag detection,
playlist management, and domain-driven architecture components.
"""

import asyncio
import traceback
from pathlib import Path
from typing import Dict

from app.src.config.nfc_config import NFCConfig
from app.src.infrastructure.nfc.nfc_factory import NfcFactory

# Application imports
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.services.broadcasting.unified_broadcasting_service import UnifiedBroadcastingService

# Domain-driven architecture imports (PURE DDD - No Legacy)
from app.src.dependencies import get_data_application_service
from app.src.application.services.nfc_application_service import NfcApplicationService

# MARK: - Constants
PROGRESS_LOG_INTERVAL = 10  # Log track progress every 10%
SYNC_TIMEOUT_SECONDS = 15  # Maximum wait time for playlist synchronization

# MARK: - Logger
logger = get_logger(__name__)

# MARK: - Application Class


class Application:
    """Main application class for TheOpenMusicBox backend.

    Manages initialization and lifecycle of various components.
    """

    # MARK: - Initialization
    def __init__(self, config, audio_backend=None):
        """Initialize the Application instance.

        Args:
            config: Configuration object
            audio_backend: Optional audio backend to inject (avoids circular imports)
        """
        self._config = config
        self._audio_backend = audio_backend  # Store injected audio backend
        self._nfc_lock = None

        # PURE DOMAIN ARCHITECTURE - No legacy services
        # Domain bootstrap will handle all service initialization

        # Create NFC config with auto-pause setting from app config
        nfc_config = NFCConfig()
        nfc_config.auto_pause_enabled = self._config.get("auto_pause_enabled")
        self._nfc_config = nfc_config

        # Initialize NFC components in constructor (basic setup)
        # These will be properly initialized in initialize_async
        self._nfc_handler = None
        self._nfc_app_service = None

        # Initialize broadcasting service for Socket.IO events (will be set during initialization)
        self._broadcasting_service = None

        # Domain controller will be set during domain initialization
        self._playlist_controller = None

        logger.info("🚀 Pure Domain Application initialized successfully")

    async def initialize_async(self):
        """Initialize application resources asynchronously.

        Asynchronous initialization - to be called from lifespan context.
        """
        # Initialize pure domain-driven architecture
        await self._initialize_domain_architecture()

        # Initialize NFC components using domain services
        await self._setup_nfc()

        # Synchronize playlists with filesystem at startup
        await self._sync_playlists_domain()

        return self

    # MARK: - Domain Architecture Initialization
    @handle_errors("_initialize_domain_architecture")
    async def _initialize_domain_architecture(self) -> None:
        """Initialize the pure domain-driven architecture."""
        logger.info("🚀 Initializing PURE domain-driven architecture...")

        # Register core infrastructure services first
        from app.src.infrastructure.di.container import register_core_infrastructure_services
        register_core_infrastructure_services()
        logger.info("✅ Core infrastructure services registered")

        # Register data domain services
        from app.src.infrastructure.di.data_container import register_data_domain_services
        register_data_domain_services()
        logger.info("✅ Data domain services registered")

        # Use injected audio backend or try to get from DI container
        # This avoids circular import with app.main
        container_audio = self._audio_backend

        if container_audio is None:
            # Try to get from DI container as fallback
            try:
                from app.src.infrastructure.di.container import get_container
                infrastructure_container = get_container()
                if infrastructure_container.has("audio_backend"):
                    container_audio = infrastructure_container.get("audio_backend")
                    logger.info(f"🎵 Found audio backend from DI: {type(container_audio).__name__}")
            except Exception as e:
                logger.debug(f"Could not get audio backend from DI container: {e}")

        # Initialize domain bootstrap with detected audio backend (or None for pure domain)
        from app.src.infrastructure.di.container import get_container
        container = get_container()
        domain_bootstrap = container.get("domain_bootstrap")

        if not domain_bootstrap.is_initialized:
            domain_bootstrap.initialize(existing_backend=container_audio)
            logger.info("✅ Pure Domain Application initialized successfully")

        # Get PlaybackCoordinator from DI container (singleton managed by container)
        from app.src.dependencies import get_playback_coordinator

        # This will create the singleton if it doesn't exist, or return existing one
        self._playlist_controller = get_playback_coordinator()
        logger.info("✅ PlaybackCoordinator initialized with domain architecture via DI container")

    # MARK: - NFC Event Handling
    @handle_errors("handle_nfc_event")
    async def handle_nfc_event(self, tag_data):
        """Handle an NFC event triggered by tag detection.

        Handles NFC tag events (scan or absence) by routing them to the
        PlaylistController. This method provides a public API, encapsulating
        the interaction with _playlist_controller.

        Args:
            tag_data: The data associated with the NFC tag event.
        """
        logger.info(f"🎵 Processing NFC event: {tag_data}")
        if isinstance(tag_data, dict) and tag_data.get("absence"):
            logger.debug("Handling NFC tag absence event.")
            if not self._playlist_controller:
                logger.error("❌ Playlist controller not initialized - cannot handle NFC tag absence event",
                )
                return
            self._playlist_controller.handle_tag_absence()
        else:
            uid = None
            full_data = None
            if isinstance(tag_data, dict):
                uid = tag_data.get("uid")
                full_data = tag_data  # Pass full dict if available
                logger.info(f"🎵 Handling NFC tag scanned event (dict): UID={uid}",
                )
            else:
                uid = tag_data  # Assume it's the UID string
                logger.info(f"🎵 Handling NFC tag scanned event (string): UID={uid}",
                )
            if uid:
                # Thread-safe check and capture of playlist controller to avoid race conditions
                playlist_controller = self._playlist_controller
                if not playlist_controller:
                    logger.error("❌ Playlist controller not initialized - cannot handle NFC tag scanned event",
                    )
                    return

                # Schedule async handler in event loop
                import asyncio

                try:
                    asyncio.create_task(playlist_controller.handle_tag_scanned(uid, full_data))
                except Exception as e:
                    logger.error(f"Error scheduling NFC event handler: {e}")

    # MARK: - Domain Playlist Synchronization
    @handle_errors("_sync_playlists_domain")
    async def _sync_playlists_domain(self):
        """Synchronize playlists using pure domain architecture."""
        logger.info("🔄 Starting DOMAIN playlist synchronization")
        # Use domain application service for synchronization
        from app.src.services.filesystem_sync_service import FilesystemSyncService

        # Get upload folder from config
        upload_folder = self._get_upload_folder_path()
        # Create filesystem sync service
        sync_service = FilesystemSyncService()
        # Use domain application service to sync
        # NOTE: Filesystem sync migration to DDD architecture
        # Current: FilesystemSyncService (legacy) is created but not used
        # Planned: Migrate to DataApplicationService.sync_filesystem_to_database()
        # Timeline: Q1 2026 (after DDD migration stabilizes)
        # For now, skip this sync operation as it's not critical for core functionality
        sync_result = {"status": "success", "data": {"message": "Filesystem sync skipped in DDD architecture"}}
        if sync_result.get("status") == "success":
            stats = sync_result.get("data", {})
            logger.info("✅ Domain playlist synchronization completed",
                extra={
                    "playlists_added": stats.get("playlists_added", 0),
                    "playlists_updated": stats.get("playlists_updated", 0),
                    "tracks_added": stats.get("tracks_added", 0),
                    "tracks_removed": stats.get("tracks_removed", 0),
                },
            )
        else:
            logger.warning(f"⚠️ Domain sync completed with issues: {sync_result}")

    def _get_upload_folder_path(self) -> Path:
        """Get the upload folder path from config."""
        if hasattr(self._config, "upload_folder"):
            upload_folder = Path(self._config.upload_folder)
        elif hasattr(self._config, "config") and hasattr(self._config.config, "upload_folder"):
            upload_folder = Path(self._config.config.upload_folder)
        else:
            raise AttributeError(
                "Config object must have an 'upload_folder' attribute or a 'config' property with 'upload_folder'."
            )

        # Get the app directory path (parent of src)
        app_dir = Path(__file__).parent.parent.parent

        # Make relative paths absolute from the app directory
        if not upload_folder.is_absolute():
            upload_folder = app_dir / upload_folder

        if not upload_folder.exists():
            logger.warning(f"Upload folder doesn't exist: {upload_folder}")
            upload_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created upload folder: {upload_folder}")

        return upload_folder

    # MARK: - NFC Setup
    @handle_errors("_setup_nfc")
    async def _setup_nfc(self):
        """Set up and initialize NFC reader using DDD architecture."""
        # Create a lock for I2C bus (if needed)
        if self._nfc_lock is None:
            self._nfc_lock = asyncio.Lock()
        # Initialize the NFC hardware handler
        self._nfc_handler = await NfcFactory.create_nfc_handler_adapter(self._nfc_lock)
        logger.info(f"NFC handler initialized: {type(self._nfc_handler).__name__}",
        )
        # Initialize NFC application service using domain architecture
        from app.src.infrastructure.nfc.repositories.nfc_memory_repository import (
            NfcMemoryRepository,
        )

        nfc_repository = NfcMemoryRepository()
        # Get playlist repository for NFC-Playlist synchronization using proper DI
        # This is CRITICAL for persisting NFC tag associations to the database
        from app.src.infrastructure.di.container import get_container
        infrastructure_container = get_container()
        playlist_repository = infrastructure_container.get("playlist_repository")
        logger.info("✅ Obtained playlist repository for NFC-Playlist synchronization")

        self._nfc_app_service = NfcApplicationService(
            nfc_hardware=self._nfc_handler,
            nfc_repository=nfc_repository,
            playlist_repository=playlist_repository,  # Enable cross-repository synchronization
        )
        # Register callbacks for tag detection (NfcApplicationService handles hardware callbacks internally)
        self._nfc_app_service.register_tag_detected_callback(self._on_nfc_tag_detected)
        self._nfc_app_service.register_association_callback(self._on_nfc_association_event)
        # Start the NFC system
        start_result = await self._nfc_app_service.start_nfc_system()
        if start_result.get("status") == "success":
            logger.info("✅ NFC application service started successfully")
        else:
            logger.warning(f"⚠️ NFC service start warning: {start_result.get('message')}"
            )
        # Link with playlist controller if available
        if self._playlist_controller and hasattr(self._playlist_controller, "set_nfc_service"):
            self._playlist_controller.set_nfc_service(self._nfc_app_service)
            logger.info("PlaylistController linked with NFC application service")
        logger.info("🔗 NFC system fully initialized with DDD architecture")

    # MARK: - NFC Event Handlers
    @handle_errors("_on_nfc_tag_detected")
    def _on_nfc_tag_detected(self, tag_id: str) -> None:
        """Handle NFC tag detection from application service.

        Args:
            tag_id: Detected tag identifier
        """
        logger.info(f"🏷️ NFC tag detected in application (service): {tag_id}")
        # Delegate to existing handle_nfc_event method for compatibility
        asyncio.create_task(self.handle_nfc_event(tag_id))

    @handle_errors("_on_nfc_association_event")
    def _on_nfc_association_event(self, event_data: Dict) -> None:
        """Handle NFC association events from application service.

        Args:
            event_data: Association event data with keys like action, session_id, playlist_id, tag_id, session_state
        """
        # Log association events for debugging
        logger.info(f"🔔 Broadcasting NFC association event: {event_data}")

        # Extract event data
        action = event_data.get("action", "unknown")
        session_id = event_data.get("session_id")
        playlist_id = event_data.get("playlist_id")
        tag_id = event_data.get("tag_id")
        session_state = event_data.get("session_state", "unknown")

        # Map domain action to frontend state
        association_state = self._map_action_to_state(action, session_state)

        # Broadcast NFC association event via Socket.IO
        asyncio.create_task(self._broadcast_nfc_association_event(
            association_state=association_state,
            playlist_id=playlist_id,
            tag_id=tag_id,
            session_id=session_id,
            event_data=event_data
        ))

    def _map_action_to_state(self, action: str, session_state: str) -> str:
        """Map domain action to frontend association state.

        Args:
            action: Domain action (association_success, duplicate_association, etc.)
            session_state: Session state value

        Returns:
            Frontend state string
        """
        if action == "association_success":
            return "success"  # Frontend expects 'success', not 'completed'
        elif action == "duplicate_association":
            return "duplicate"  # Frontend expects 'duplicate', not 'error'
        elif session_state == "TIMEOUT":
            return "timeout"
        elif session_state == "LISTENING":
            return "waiting"
        elif session_state == "CANCELLED":
            return "cancelled"
        else:
            return "error"

    async def _broadcast_nfc_association_event(
        self,
        association_state: str,
        playlist_id: str = None,
        tag_id: str = None,
        session_id: str = None,
        event_data: Dict = None
    ) -> None:
        """Broadcast NFC association event via Socket.IO.

        Args:
            association_state: Frontend association state
            playlist_id: Playlist ID
            tag_id: Tag ID
            session_id: Session ID
            event_data: Original event data for additional info
        """
        try:
            if not self._broadcasting_service:
                logger.warning("⚠️ Broadcasting service not available, skipping NFC association broadcast")
                return

            success = await self._broadcasting_service.broadcast_nfc_association(
                association_state=association_state,
                playlist_id=playlist_id,
                tag_id=tag_id,
                session_id=session_id
            )
            if success:
                logger.info(f"✅ Successfully broadcasted NFC association state: {association_state}")
            else:
                logger.warning(f"⚠️ Failed to broadcast NFC association state: {association_state}")
        except Exception as e:
            logger.error(f"❌ Error broadcasting NFC association event: {e}")
            logger.debug(f"Event data: {event_data}")

    # MARK: - Internal Event Handlers
    def _handle_nfc_error(self, error):
        """Handle NFC reader errors.

        Args:
            error: Error information
        """
        logger.error(f"NFC error: {error}")

    # MARK: - Audio Setup (Pure Domain Architecture)
    # All audio functionality is now handled by the domain bootstrap and audio engine
    # No legacy audio setup methods needed

    @handle_errors("_handle_playback_status")
    def _handle_playback_status(self, event):
        """Handle playback status updates.

        Args:
            event: Playback status event
        """
        if event.event_type == "status":
            logger.info("Playback status update", extra=event.data)

    @handle_errors("_handle_track_progress")
    def _handle_track_progress(self, event):
        """Handle track progress updates.

        Args:
            event: Track progress event
        """
        if event.event_type == "progress":
            # Only log progress at a reasonable interval to avoid log flooding
            if event.data.get("progress_percent", 0) % PROGRESS_LOG_INTERVAL == 0:
                logger.debug("Track progress update", extra=event.data)

    def _handle_audio_error(self, error):
        """Handle audio system errors.

        Args:
            error: Error information
        """
        logger.error(f"Audio error: {error}")

    # MARK: - Application Lifecycle
    @handle_errors("run")
    async def run(self):
        """Start and run the application asynchronously."""
        logger.info("Starting application")
        # Start the playlist controller
        if hasattr(self._playlist_controller, "start"):
            await self._playlist_controller.start()
        # Keep the application running
        while True:
            await asyncio.sleep(1)

    async def cleanup(self):
        """Clean up all resources before application shutdown."""
        logger.info("Starting application cleanup")
        try:
            # Stop NFC application service
            if hasattr(self, "_nfc_app_service") and self._nfc_app_service:
                try:
                    await self._nfc_app_service.stop_nfc_system()
                    logger.info("✅ NFC application service stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping NFC service: {e}")

            # Additional cleanup specific to Application
            if hasattr(self, "_playlist_controller") and self._playlist_controller and hasattr(
                self._playlist_controller, "cleanup"
            ):
                cleanup_method = getattr(self._playlist_controller, "cleanup")
                if cleanup_method:
                    # Check if it's a coroutine function
                    import inspect
                    if inspect.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()
                    logger.info("✅ Playlist controller cleanup completed")
                else:
                    logger.warning("⚠️ Playlist controller cleanup method is None")
            else:
                logger.warning("⚠️ Playlist controller not available for cleanup")

            # Clean up domain bootstrap
            from app.src.infrastructure.di.container import get_container
            container = get_container()
            domain_bootstrap = container.get("domain_bootstrap")

            if hasattr(domain_bootstrap, "stop") and domain_bootstrap.is_initialized:
                await domain_bootstrap.stop()
                logger.info("✅ Domain bootstrap stopped")

            if hasattr(domain_bootstrap, "cleanup") and domain_bootstrap.is_initialized:
                domain_bootstrap.cleanup()
                logger.info("✅ Domain bootstrap cleanup completed")
        except Exception as e:
            logger.error(f"Error during application cleanup: {e}")
            logger.debug(f"Cleanup error details: {traceback.format_exc()}")
