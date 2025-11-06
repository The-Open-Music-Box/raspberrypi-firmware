# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for initial schema migration."""

import sqlite3
import tempfile
import os
import pytest
import importlib
from unittest.mock import patch, Mock

# Import migration module with numeric name using importlib
migration_module = importlib.import_module('app.src.data.migrations.001_initial_schema')
up = migration_module.up
down = migration_module.down
get_migration_info = migration_module.get_migration_info
migrate_database = migration_module.migrate_database
verify_migration = migration_module.verify_migration
MIGRATION_VERSION = migration_module.MIGRATION_VERSION
MIGRATION_NAME = migration_module.MIGRATION_NAME


class TestMigrationUp:
    """Test up() migration function."""

    def test_up_creates_tables(self):
        """Test that up() creates playlists and tracks tables."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)
            result = up(connection)

            assert result is True

            # Verify playlists table exists
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playlists'")
            assert cursor.fetchone() is not None

            # Verify tracks table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'")
            assert cursor.fetchone() is not None

            connection.close()
        finally:
            os.unlink(db_path)

    def test_up_creates_indexes(self):
        """Test that up() creates necessary indexes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)
            result = up(connection)

            assert result is True

            # Verify indexes exist
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]

            assert "idx_tracks_playlist_id" in indexes
            assert "idx_tracks_track_number" in indexes
            assert "idx_playlists_nfc_tag_id" in indexes

            connection.close()
        finally:
            os.unlink(db_path)

    def test_up_is_idempotent(self):
        """Test that up() can be run multiple times safely."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)

            # Run migration twice
            result1 = up(connection)
            result2 = up(connection)

            assert result1 is True
            assert result2 is True

            connection.close()
        finally:
            os.unlink(db_path)

    def test_up_handles_errors(self):
        """Test that up() handles errors gracefully."""
        # Create a mock connection that raises an error
        mock_connection = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = sqlite3.OperationalError("Database error")
        mock_connection.cursor.return_value = mock_cursor

        result = up(mock_connection)

        assert result is False
        mock_connection.rollback.assert_called_once()

    def test_up_commits_changes(self):
        """Test that up() commits changes to database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)
            result = up(connection)

            assert result is True

            # Close and reopen connection to verify commit
            connection.close()
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert "playlists" in tables
            assert "tracks" in tables

            connection.close()
        finally:
            os.unlink(db_path)


class TestMigrationDown:
    """Test down() rollback function."""

    def test_down_drops_tables(self):
        """Test that down() drops tables."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)

            # First apply migration
            up(connection)

            # Then rollback
            result = down(connection)

            assert result is True

            # Verify tables don't exist
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert "playlists" not in tables
            assert "tracks" not in tables

            connection.close()
        finally:
            os.unlink(db_path)

    def test_down_is_idempotent(self):
        """Test that down() can be run multiple times safely."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)

            # Run rollback twice (even without tables existing)
            result1 = down(connection)
            result2 = down(connection)

            assert result1 is True
            assert result2 is True

            connection.close()
        finally:
            os.unlink(db_path)

    def test_down_handles_errors(self):
        """Test that down() handles errors gracefully."""
        # Create a mock connection that raises an error
        mock_connection = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = sqlite3.OperationalError("Database error")
        mock_connection.cursor.return_value = mock_cursor

        result = down(mock_connection)

        assert result is False
        mock_connection.rollback.assert_called_once()

    def test_down_commits_changes(self):
        """Test that down() commits changes to database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)
            up(connection)
            down(connection)

            # Close and reopen connection to verify commit
            connection.close()
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert "playlists" not in tables
            assert "tracks" not in tables

            connection.close()
        finally:
            os.unlink(db_path)


class TestMigrationInfo:
    """Test migration metadata."""

    def test_get_migration_info_returns_dict(self):
        """Test that get_migration_info() returns a dictionary."""
        info = get_migration_info()

        assert isinstance(info, dict)

    def test_get_migration_info_has_version(self):
        """Test that info contains version."""
        info = get_migration_info()

        assert "version" in info
        assert info["version"] == MIGRATION_VERSION
        assert info["version"] == "001"

    def test_get_migration_info_has_name(self):
        """Test that info contains name."""
        info = get_migration_info()

        assert "name" in info
        assert info["name"] == MIGRATION_NAME
        assert info["name"] == "initial_schema"

    def test_get_migration_info_has_description(self):
        """Test that info contains description."""
        info = get_migration_info()

        assert "description" in info
        assert isinstance(info["description"], str)
        assert len(info["description"]) > 0


class TestMigrateDatabase:
    """Test migrate_database() wrapper function."""

    def test_migrate_database_success(self):
        """Test successful database migration."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            result = migrate_database(db_path)

            assert result is True

            # Verify migration was applied
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playlists'")
            assert cursor.fetchone() is not None
            connection.close()
        finally:
            os.unlink(db_path)

    def test_migrate_database_creates_file(self):
        """Test that migrate_database creates database file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            result = migrate_database(db_path)

            assert result is True
            assert os.path.exists(db_path)

    def test_migrate_database_handles_invalid_path(self):
        """Test that migrate_database handles invalid paths gracefully."""
        result = migrate_database("/nonexistent/path/database.db")

        assert result is False

    def test_migrate_database_handles_errors(self):
        """Test that migrate_database handles errors."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("Connection failed")

            result = migrate_database("test.db")

            assert result is False


class TestVerifyMigration:
    """Test verify_migration() function."""

    def test_verify_migration_success(self):
        """Test verifying a successfully applied migration."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            # Apply migration
            migrate_database(db_path)

            # Verify it
            result = verify_migration(db_path)

            assert result is True
        finally:
            os.unlink(db_path)

    def test_verify_migration_missing_playlists_table(self):
        """Test verification fails when playlists table is missing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            # Create database with only tracks table
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE tracks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            connection.commit()
            connection.close()

            # Verify should fail
            result = verify_migration(db_path)

            assert result is False
        finally:
            os.unlink(db_path)

    def test_verify_migration_missing_tracks_table(self):
        """Test verification fails when tracks table is missing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            # Create database with only playlists table
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE playlists (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            connection.commit()
            connection.close()

            # Verify should fail
            result = verify_migration(db_path)

            assert result is False
        finally:
            os.unlink(db_path)

    def test_verify_migration_empty_database(self):
        """Test verification fails on empty database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            # Create empty database
            connection = sqlite3.connect(db_path)
            connection.close()

            # Verify should fail
            result = verify_migration(db_path)

            assert result is False
        finally:
            os.unlink(db_path)

    def test_verify_migration_handles_invalid_path(self):
        """Test that verify_migration handles invalid paths gracefully."""
        result = verify_migration("/nonexistent/path/database.db")

        assert result is False

    def test_verify_migration_handles_errors(self):
        """Test that verify_migration handles errors."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("Connection failed")

            result = verify_migration("test.db")

            assert result is False


class TestMigrationIntegration:
    """Test full migration workflow."""

    def test_full_migration_cycle(self):
        """Test complete migration cycle: up -> verify -> down."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            # Apply migration
            connection = sqlite3.connect(db_path)
            assert up(connection) is True

            # Verify migration
            assert verify_migration(db_path) is True

            # Rollback
            assert down(connection) is True

            # Verify rollback
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "playlists" not in tables
            assert "tracks" not in tables

            connection.close()
        finally:
            os.unlink(db_path)

    def test_migration_with_data(self):
        """Test that migration allows inserting data."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)
            up(connection)

            # Insert test data
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO playlists (id, title, description)
                VALUES ('pl-1', 'Test Playlist', 'Test Description')
            """)
            cursor.execute("""
                INSERT INTO tracks (id, playlist_id, track_number, title)
                VALUES ('track-1', 'pl-1', 1, 'Test Track')
            """)
            connection.commit()

            # Verify data was inserted
            cursor.execute("SELECT COUNT(*) FROM playlists")
            assert cursor.fetchone()[0] == 1

            cursor.execute("SELECT COUNT(*) FROM tracks")
            assert cursor.fetchone()[0] == 1

            connection.close()
        finally:
            os.unlink(db_path)

    def test_foreign_key_constraint(self):
        """Test that foreign key constraint is enforced."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            db_path = tmp.name

        try:
            connection = sqlite3.connect(db_path)
            connection.execute("PRAGMA foreign_keys = ON")
            up(connection)

            cursor = connection.cursor()

            # Try to insert track with non-existent playlist_id
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO tracks (id, playlist_id, track_number, title)
                    VALUES ('track-1', 'nonexistent-pl', 1, 'Test Track')
                """)
                connection.commit()

            connection.close()
        finally:
            os.unlink(db_path)
