# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Pure DDD Database Manager

Infrastructure service that provides database connectivity following DDD principles.
Implements the domain's PersistenceServiceProtocol using SQLite.
"""

from app.src.infrastructure.database.sqlite_database_service import SQLiteDatabaseService
from app.src.monitoring import get_logger
from app.src.config import config
import threading

# Optional migration support - will be None if not available
try:
    from app.src.data.migrations.migration_runner import MigrationRunner
except ImportError:
    MigrationRunner = None

logger = get_logger(__name__)


class DatabaseManager:
    """Pure DDD Database Manager - Infrastructure Service Layer.

    This infrastructure service provides database connectivity following DDD principles.
    It delegates to SQLiteDatabaseService for actual operations.
    Singleton lifecycle is managed by the DI container.
    """

    def __init__(self, db_path: str = None):
        """Initialize DatabaseManager.

        Args:
            db_path: Path to database file. If None, uses config.db_file
        """
        if db_path is None:
            db_path = config.db_file

        # Initialize the SQLite database service
        self._database_service = SQLiteDatabaseService(
            database_path=db_path,
            pool_size=5
        )

        self._migration_runner = MigrationRunner(db_path) if MigrationRunner else None

        # Run migrations if available
        self._run_migrations()

        logger.info("✅ Pure DDD Database Manager initialized")

    def _run_migrations(self):
        """Run database migrations if migration runner is available."""
        if self._migration_runner:
            try:
                self._migration_runner.run_migrations()
                logger.info("✅ Database migrations completed")
            except Exception as e:
                logger.error(f"❌ Migration failed: {e}")
                raise

    @property
    def database_service(self) -> SQLiteDatabaseService:
        """Get the database service for repositories.

        Returns:
            SQLiteDatabaseService instance for database operations
        """
        return self._database_service

    def get_health_info(self) -> dict:
        """Get database health information."""
        return self._database_service.get_health_info()

    def cleanup(self):
        """Clean up database manager resources."""
        if hasattr(self, '_database_service'):
            self._database_service.cleanup()
            logger.info("✅ Database manager cleaned up")


# Database manager should be retrieved from DI container
# Example: container.get("database_manager")
# The DI container manages the singleton lifecycle
