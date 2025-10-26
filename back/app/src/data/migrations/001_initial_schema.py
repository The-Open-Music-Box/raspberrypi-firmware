#!/usr/bin/env python3
"""
Migration 001: Initial Schema
Creates the base tables for TheOpenMusicBox: playlists and tracks
"""

import sqlite3
from typing import Dict, Any
from app.src.monitoring import get_logger

logger = get_logger(__name__)

MIGRATION_VERSION = "001"
MIGRATION_NAME = "initial_schema"


def up(connection: sqlite3.Connection) -> bool:
    """Apply the migration - create initial schema."""
    try:
        cursor = connection.cursor()

        # Create playlists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                nfc_tag_id TEXT,
                path TEXT,
                type TEXT DEFAULT 'album',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create tracks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id TEXT PRIMARY KEY,
                playlist_id TEXT NOT NULL,
                track_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                filename TEXT,
                file_path TEXT,
                duration_ms INTEGER,
                artist TEXT,
                album TEXT,
                play_count INTEGER DEFAULT 0,
                server_seq INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_playlist_id ON tracks(playlist_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_track_number ON tracks(track_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_playlists_nfc_tag_id ON playlists(nfc_tag_id)")

        connection.commit()
        logger.info(f"✅ Migration {MIGRATION_VERSION} applied successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration {MIGRATION_VERSION} failed: {e}")
        connection.rollback()
        return False


def down(connection: sqlite3.Connection) -> bool:
    """Rollback the migration - drop tables."""
    try:
        cursor = connection.cursor()

        # Drop tables in reverse dependency order
        cursor.execute("DROP TABLE IF EXISTS tracks")
        cursor.execute("DROP TABLE IF EXISTS playlists")

        connection.commit()
        logger.info(f"✅ Migration {MIGRATION_VERSION} rolled back successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Migration {MIGRATION_VERSION} rollback failed: {e}")
        connection.rollback()
        return False


def get_migration_info() -> Dict[str, Any]:
    """Get migration metadata."""
    return {
        "version": MIGRATION_VERSION,
        "name": MIGRATION_NAME,
        "description": "Creates initial database schema with playlists and tracks tables"
    }


def migrate_database(db_path: str) -> bool:
    """Migration runner interface - applies the migration."""
    try:
        with sqlite3.connect(db_path) as connection:
            return up(connection)
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return False


def verify_migration(db_path: str) -> bool:
    """Verify the migration was applied correctly."""
    try:
        with sqlite3.connect(db_path) as connection:
            cursor = connection.cursor()

            # Check if playlists table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playlists'")
            if not cursor.fetchone():
                return False

            # Check if tracks table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'")
            if not cursor.fetchone():
                return False

            return True
    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")
        return False