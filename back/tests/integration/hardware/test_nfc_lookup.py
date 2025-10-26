#!/usr/bin/env python3
# Test script to verify NFC tag to playlist lookup

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

async def test_nfc_lookup():
    """Test NFC tag to playlist lookup."""
    tag_uid = "53a8f6db600001"
    
    logger.log(LogLevel.INFO, f"🔍 Testing playlist lookup for NFC tag: {tag_uid}")
    
    try:
        # Test the lookup
        logger.log(LogLevel.INFO, "📋 Testing with playlist application service...")
        playlist_app_service = get_data_application_service()
        playlist_data = await playlist_app_service.get_playlist_by_nfc_tag(tag_uid)
        logger.log(LogLevel.INFO, f"📋 Application service returned: {playlist_data}")
        
        if playlist_data:
            logger.log(LogLevel.INFO, f"✅ Found playlist: {playlist_data.get('title')}")
            logger.log(LogLevel.INFO, f"📋 Playlist ID: {playlist_data.get('id')}")
            logger.log(LogLevel.INFO, f"🎵 Track count: {len(playlist_data.get('tracks', []))}")
            return True
        else:
            logger.log(LogLevel.WARNING, f"❌ No playlist found for tag: {tag_uid}")
            return False
            
    except Exception as e:
        logger.log(LogLevel.ERROR, f"❌ Error during lookup: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_nfc_lookup())
    sys.exit(0 if success else 1)