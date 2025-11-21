# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Migration Runner for database schema management

Handles migration versioning, execution, and rollback.
"""

import sqlite3
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import re

from app.src.monitoring import get_logger

logger = get_logger(__name__)


class Migration:
    """Represents a single database migration."""

    def __init__(self, version: str, name: str, file_path: Path):
        self.version = version
        self.name = name
        self.file_path = file_path
        self._module = None

    @property
    def module(self):
        """Lazy load the migration module."""
        if self._module is None:
            spec = importlib.util.spec_from_file_location(
                f"migration_{self.version}", self.file_path
            )
            self._module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self._module)
        return self._module

    def migrate(self, db_path: str) -> bool:
        """Execute the migration."""
        try:
            if hasattr(self.module, "migrate_database"):
                return self.module.migrate_database(db_path)
            else:
                logger.error(f"Migration {self.version} missing migrate_database function"
                )
                return False
        except (ImportError, AttributeError, sqlite3.Error) as e:
            logger.error(f"Migration {self.version} failed: {str(e)}")
            return False

    def verify(self, db_path: str) -> bool:
        """Verify the migration was successful."""
        try:
            if hasattr(self.module, "verify_migration"):
                return self.module.verify_migration(db_path)
            else:
                # No verification function, assume success
                return True
        except (ImportError, AttributeError, sqlite3.Error) as e:
            logger.error(f"Migration {self.version} verification failed: {str(e)}")
            return False


class MigrationRunner:
    """Manages database migrations with versioning."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """Create the migration tracking table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    success BOOLEAN NOT NULL DEFAULT 0
                )
            """
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to create migration table: {str(e)}")

    def _get_applied_migrations(self) -> List[str]:
        """Get list of successfully applied migration versions."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT version FROM schema_migrations WHERE success = 1 ORDER BY version"
            )
            versions = [row[0] for row in cursor.fetchall()]
            conn.close()
            return versions
        except sqlite3.Error:
            return []

    def _record_migration(self, migration: Migration, success: bool):
        """Record a migration attempt in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            applied_at = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                INSERT OR REPLACE INTO schema_migrations (version, name, applied_at, success)
                VALUES (?, ?, ?, ?)
            """,
                (migration.version, migration.name, applied_at, success),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Failed to record migration: {str(e)}")

    def _discover_migrations(self) -> List[Migration]:
        """Discover all migration files in the migrations directory."""
        migrations = []

        # Pattern for migration files: NNN_description.py
        pattern = re.compile(r"^(\d{3})_(.+)\.py$")

        for file_path in self.migrations_dir.glob("*.py"):
            if file_path.name == "__init__.py" or file_path.name == "migration_runner.py":
                continue

            match = pattern.match(file_path.name)
            if match:
                version = match.group(1)
                name = match.group(2).replace("_", " ").title()
                migrations.append(Migration(version, name, file_path))

        # Sort by version number
        migrations.sort(key=lambda m: m.version)
        return migrations

    def needs_migration(self) -> bool:
        """Check if any pending migrations exist."""
        all_migrations = self._discover_migrations()
        applied_migrations = self._get_applied_migrations()

        for migration in all_migrations:
            if migration.version not in applied_migrations:
                return True

        return False

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations."""
        all_migrations = self._discover_migrations()
        applied_migrations = self._get_applied_migrations()

        pending = []
        for migration in all_migrations:
            if migration.version not in applied_migrations:
                pending.append(migration)

        return pending

    def run_migrations(self) -> bool:
        """Run all pending migrations."""
        pending_migrations = self.get_pending_migrations()

        if not pending_migrations:
            logger.info("No pending migrations")
            return True

        logger.info(f"Running {len(pending_migrations)} pending migrations...")

        for migration in pending_migrations:
            logger.info(f"Applying migration {migration.version}: {migration.name}")

            # Run the migration
            success = migration.migrate(self.db_path)

            if success:
                # Verify the migration
                verified = migration.verify(self.db_path)
                if verified:
                    self._record_migration(migration, True)
                    logger.info(f"Migration {migration.version} completed successfully"
                    )
                else:
                    self._record_migration(migration, False)
                    logger.error(f"Migration {migration.version} verification failed")
                    return False
            else:
                self._record_migration(migration, False)
                logger.error(f"Migration {migration.version} failed")
                return False

        logger.info("All migrations completed successfully")
        return True

    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        all_migrations = self._discover_migrations()
        applied_migrations = self._get_applied_migrations()
        pending_migrations = self.get_pending_migrations()

        return {
            "total_migrations": len(all_migrations),
            "applied_migrations": len(applied_migrations),
            "pending_migrations": len(pending_migrations),
            "last_applied_version": applied_migrations[-1] if applied_migrations else None,
            "needs_migration": len(pending_migrations) > 0,
        }
