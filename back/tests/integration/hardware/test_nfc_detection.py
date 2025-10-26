#!/usr/bin/env python3
# Quick test script to verify NFC detection chain works

import asyncio
import sys
from pathlib import Path

# Add app to Python path
app_path = Path(__file__).parent / "app"
sys.path.insert(0, str(app_path))

from app.src.infrastructure.nfc.nfc_factory import NfcFactory
from app.src.monitoring.logging.log_level import LogLevel
from app.src.monitoring import get_logger

logger = get_logger(__name__)

async def test_nfc_detection():
    """Test NFC detection functionality."""
    logger.log(LogLevel.INFO, "🧪 Starting NFC detection test...")
    
    # Create NFC handler
    nfc_lock = asyncio.Lock()
    nfc_handler = await NfcFactory.create_nfc_handler_adapter(nfc_lock)
    
    # Test callback counter
    detection_count = 0
    
    def test_callback(tag_uid: str):
        nonlocal detection_count
        detection_count += 1
        logger.log(LogLevel.INFO, f"🎯 TEST CALLBACK TRIGGERED! Tag: {tag_uid} (count: {detection_count})")
    
    # Register callback
    nfc_handler.set_tag_detected_callback(test_callback)
    logger.log(LogLevel.INFO, "✅ Test callback registered")
    
    # Start detection
    await nfc_handler.start_nfc_reader()
    logger.log(LogLevel.INFO, "✅ NFC reader started")
    
    # If using Mock hardware, simulate tag detection
    if nfc_handler._is_mock:
        logger.log(LogLevel.INFO, "🧪 Mock hardware detected - simulating tag...")
        # Simulate hardware tag event directly
        test_tag_data = {"uid": "TEST123456", "action": "detected"}
        nfc_handler._on_hardware_tag_event(test_tag_data)
    
    # Wait a bit for real hardware detection
    logger.log(LogLevel.INFO, "⏳ Waiting 10 seconds for tag detection...")
    await asyncio.sleep(10)
    
    # Stop detection
    await nfc_handler.stop_nfc_reader()
    logger.log(LogLevel.INFO, "✅ NFC reader stopped")
    
    # Report results
    if detection_count > 0:
        logger.log(LogLevel.INFO, f"🎉 SUCCESS! Detected {detection_count} tags")
    else:
        logger.log(LogLevel.WARNING, "⚠️  No tags detected during test")
    
    # Cleanup
    nfc_handler.cleanup()
    logger.log(LogLevel.INFO, "🧹 Test cleanup completed")

if __name__ == "__main__":
    asyncio.run(test_nfc_detection())