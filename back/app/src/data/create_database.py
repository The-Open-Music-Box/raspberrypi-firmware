#!/usr/bin/env python3
"""
Database Creation Script for TheOpenMusicBox

Simple script to create a fresh database with the correct schema.
Usage: python app/src/data/create_database.py [db_path]
"""

import sqlite3
import sys
from pathlib import Path

try:
    from app.src.monitoring import get_logger
    logger = get_logger(__name__)
    USE_LOGGER = True
except ImportError:
    # Fallback when run as standalone script
    USE_LOGGER = False


def create_fresh_database(db_path: str) -> bool:
    """Create a fresh database with the complete schema."""
    try:
        # Ensure directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Delete existing database if it exists
        if db_file.exists():
            db_file.unlink()
            msg = f"✅ Deleted existing database: {db_path}"
            if USE_LOGGER:
                logger.info(msg)
            print(msg)

        # Create new database with schema
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Create schema_migrations table
            cursor.execute("""
                CREATE TABLE schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    success BOOLEAN NOT NULL DEFAULT 0
                )
            """)

            # Create playlists table
            cursor.execute("""
                CREATE TABLE playlists (
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
                CREATE TABLE tracks (
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

            conn.commit()
            msg = f"✅ Created fresh database with schema: {db_path}"
            if USE_LOGGER:
                logger.info(msg)
            print(msg)

            # Verify tables were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            msg = f"✅ Tables created: {', '.join(tables)}"
            if USE_LOGGER:
                logger.info(msg)
            print(msg)

            return True

    except Exception as e:
        msg = f"❌ Failed to create database: {e}"
        if USE_LOGGER:
            logger.error(msg)
        print(msg)
        return False


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "app/data/app.db"
    success = create_fresh_database(db_path)
    sys.exit(0 if success else 1)