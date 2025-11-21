#!/usr/bin/env python3
# Test script to verify playlist synchronization

import asyncio
import sys
from pathlib import Path

# Add app to Python path
app_path = Path(__file__).parent / "app"
sys.path.insert(0, str(app_path))

from app.src.dependencies import get_data_application_service
from app.src.monitoring.logging.log_level import LogLevel
from app.src.monitoring import get_logger

logger = get_logger(__name__)

async def test_sync():
    """Test playlist synchronization."""
    logger.log(LogLevel.INFO, "🔄 Testing playlist synchronization...")
    
    try:
        # Test sync with uploads folder
        upload_folder = Path(__file__).parent / "uploads"
        
        logger.log(LogLevel.INFO, f"📁 Syncing with folder: {upload_folder}")
        
        # Get application service via dependency injection
        playlist_app_service = get_data_application_service()

        # Call sync method
        sync_result = await playlist_app_service.sync_playlists_with_filesystem_use_case(
            upload_folder_path=str(upload_folder)
        )
        
        logger.log(LogLevel.INFO, f"📋 Sync result: {sync_result}")
        
        # Check what we have in DB after sync
        import sqlite3
        with sqlite3.connect("app/data/app.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM playlist_tracks")
            track_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM playlists")
            playlist_count = cursor.fetchone()[0]
            
            logger.log(LogLevel.INFO, f"📊 After sync: {playlist_count} playlists, {track_count} tracks")
            
            if track_count > 0:
                cursor = conn.execute("""
                    SELECT p.title, COUNT(t.id) as tracks 
                    FROM playlists p 
                    LEFT JOIN playlist_tracks t ON p.id = t.playlist_id 
                    GROUP BY p.id, p.title 
                    HAVING COUNT(t.id) > 0
                    LIMIT 5
                """)
                playlists_with_tracks = cursor.fetchall()
                logger.log(LogLevel.INFO, f"🎵 Playlists with tracks: {playlists_with_tracks}")
        
        return sync_result.get("status") == "success"
        
    except Exception as e:
        logger.log(LogLevel.ERROR, f"❌ Error during sync test: {e}")
        import traceback
        logger.log(LogLevel.ERROR, f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sync())
    sys.exit(0 if success else 1)