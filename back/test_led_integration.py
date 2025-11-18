#!/usr/bin/env python3
# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Test script to verify LED integration with the application.

This simulates the bootstrap startup sequence to ensure LED components
are properly created, injected, and initialized.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see all the details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_led_integration():
    """Test LED integration from DI container through bootstrap."""
    try:
        logger.info("="*70)
        logger.info("LED INTEGRATION TEST")
        logger.info("="*70)

        # Step 1: Register infrastructure services (including LED)
        logger.info("\n📦 Step 1: Registering infrastructure services...")
        from app.src.infrastructure.di.container import register_core_infrastructure_services
        register_core_infrastructure_services()
        logger.info("✅ Infrastructure services registered")

        # Step 2: Get DI container and create bootstrap
        logger.info("\n📦 Step 2: Creating domain bootstrap with LED injection...")
        from app.src.infrastructure.di.container import get_container
        container = get_container()
        domain_bootstrap = container.get("domain_bootstrap")
        logger.info(f"✅ Domain bootstrap created: {domain_bootstrap}")

        # Step 3: Initialize bootstrap
        logger.info("\n🔧 Step 3: Initializing domain bootstrap...")
        domain_bootstrap.initialize()
        logger.info("✅ Domain bootstrap initialized")

        # Step 4: Start bootstrap (should trigger LED STARTING state)
        logger.info("\n🚀 Step 4: Starting domain bootstrap (should show STARTING LED)...")
        await domain_bootstrap.start()
        logger.info("✅ Domain bootstrap started")

        # Give LED time to display
        logger.info("\n⏱️  Waiting 5 seconds to observe LED states...")
        await asyncio.sleep(5)

        # Step 5: Check LED status
        logger.info("\n📊 Step 5: Checking LED status...")
        if domain_bootstrap._led_manager:
            status = domain_bootstrap._led_manager.get_status()
            logger.info(f"LED Status: {status}")
        else:
            logger.error("❌ LED manager not available in bootstrap!")

        # Step 6: Stop bootstrap
        logger.info("\n🛑 Step 6: Stopping domain bootstrap...")
        await domain_bootstrap.stop()
        logger.info("✅ Domain bootstrap stopped")

        logger.info("\n" + "="*70)
        logger.info("✅ LED INTEGRATION TEST COMPLETED")
        logger.info("="*70)

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    logger.info("Starting LED integration test...")
    logger.info("This will test the LED system initialization without starting the full app\n")

    try:
        asyncio.run(test_led_integration())
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
        sys.exit(0)
