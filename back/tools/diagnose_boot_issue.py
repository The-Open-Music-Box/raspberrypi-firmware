#!/usr/bin/env python3
"""Diagnostic script to investigate boot initialization issues.

This script helps debug the "Playlist controller not initialized" error
by testing each component of the initialization sequence individually.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_step(step_name: str, test_func):
    """Run a test step and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {step_name}")
    print('='*60)
    try:
        await test_func()
        print(f"✅ {step_name} - PASSED")
        return True
    except Exception as e:
        print(f"❌ {step_name} - FAILED: {e}")
        logger.exception(f"Error in {step_name}")
        return False


async def test_config_loading():
    """Test configuration loading."""
    from app.src.config import config
    logger.info(f"Config loaded: {type(config).__name__}")
    logger.info(f"Hardware mode: USE_MOCK_HARDWARE={config.hardware.use_mock_hardware}")
    logger.info(f"Upload folder: {config.upload_folder}")


async def test_di_container():
    """Test DI container registration."""
    from app.src.infrastructure.di.container import get_container, register_core_infrastructure_services

    container = get_container()
    logger.info("DI container obtained")

    # Register core services
    register_core_infrastructure_services()
    logger.info("Core infrastructure services registered")

    # Check critical services
    services_to_check = [
        "config",
        "domain_bootstrap",
        "led_controller",
        "led_state_manager",
        "led_event_handler",
    ]

    for service_name in services_to_check:
        has_service = container.has(service_name)
        logger.info(f"Service '{service_name}': {'✅ registered' if has_service else '❌ NOT registered'}")


async def test_led_controller():
    """Test LED controller initialization."""
    from app.src.infrastructure.di.container import get_container

    container = get_container()

    try:
        led_controller = container.get("led_controller")
        logger.info(f"LED controller created: {type(led_controller).__name__}")

        # Check if it's initialized
        if hasattr(led_controller, 'is_initialized'):
            logger.info(f"LED controller initialized: {led_controller.is_initialized}")

        # Try to initialize if not already
        if hasattr(led_controller, 'initialize'):
            try:
                led_controller.initialize()
                logger.info("LED controller initialize() called successfully")
            except Exception as e:
                logger.warning(f"LED controller initialize() failed: {e}")

    except Exception as e:
        logger.error(f"Failed to get LED controller: {e}")
        raise


async def test_led_state_manager():
    """Test LED state manager initialization."""
    from app.src.infrastructure.di.container import get_container

    container = get_container()

    try:
        led_state_manager = container.get("led_state_manager")
        logger.info(f"LED state manager created: {type(led_state_manager).__name__}")

        # Try to initialize
        if hasattr(led_state_manager, 'initialize'):
            await led_state_manager.initialize()
            logger.info("LED state manager initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize LED state manager: {e}")
        raise


async def test_domain_bootstrap_creation():
    """Test domain bootstrap creation."""
    from app.src.infrastructure.di.container import get_container

    container = get_container()
    domain_bootstrap = container.get("domain_bootstrap")

    logger.info(f"Domain bootstrap created: {type(domain_bootstrap).__name__}")
    logger.info(f"Is initialized: {domain_bootstrap.is_initialized}")
    logger.info(f"Has LED manager: {domain_bootstrap._led_manager is not None}")
    logger.info(f"Has LED event handler: {domain_bootstrap._led_event_handler is not None}")


async def test_domain_bootstrap_initialization():
    """Test domain bootstrap initialization."""
    from app.src.infrastructure.di.container import get_container

    container = get_container()
    domain_bootstrap = container.get("domain_bootstrap")

    if not domain_bootstrap.is_initialized:
        logger.info("Initializing domain bootstrap...")
        domain_bootstrap.initialize()
        logger.info(f"Domain bootstrap initialized: {domain_bootstrap.is_initialized}")
    else:
        logger.info("Domain bootstrap already initialized")


async def test_domain_bootstrap_start():
    """Test domain bootstrap start (includes LED initialization)."""
    from app.src.infrastructure.di.container import get_container

    container = get_container()
    domain_bootstrap = container.get("domain_bootstrap")

    if not domain_bootstrap.is_initialized:
        raise RuntimeError("Domain bootstrap not initialized - run initialization test first")

    logger.info("Starting domain bootstrap...")
    await domain_bootstrap.start()
    logger.info("Domain bootstrap started successfully")


async def test_data_domain_services():
    """Test data domain services registration."""
    from app.src.infrastructure.di.data_container import register_data_domain_services

    logger.info("Registering data domain services...")
    register_data_domain_services()
    logger.info("Data domain services registered")


async def test_application_container():
    """Test application container and service registration."""
    from app.src.application.di.application_container import get_application_container

    app_container = get_application_container()
    logger.info("Application container obtained")


async def test_playback_coordinator():
    """Test playback coordinator creation."""
    from app.src.dependencies import get_playback_coordinator

    logger.info("Creating playback coordinator...")
    coordinator = get_playback_coordinator()

    if coordinator is None:
        raise RuntimeError("Playback coordinator is None!")

    logger.info(f"Playback coordinator created: {type(coordinator).__name__}")
    logger.info(f"Has audio backend: {coordinator._audio_backend is not None}")


async def main():
    """Run all diagnostic tests in sequence."""
    print("\n" + "="*60)
    print("OpenMusicBox Boot Diagnostic Tool")
    print("="*60)

    tests = [
        ("Configuration Loading", test_config_loading),
        ("DI Container Setup", test_di_container),
        ("LED Controller Creation", test_led_controller),
        ("LED State Manager Creation", test_led_state_manager),
        ("Domain Bootstrap Creation", test_domain_bootstrap_creation),
        ("Domain Bootstrap Initialization", test_domain_bootstrap_initialization),
        ("Domain Bootstrap Start", test_domain_bootstrap_start),
        ("Data Domain Services", test_data_domain_services),
        ("Application Container", test_application_container),
        ("Playback Coordinator Creation", test_playback_coordinator),
    ]

    results = []
    for test_name, test_func in tests:
        result = await test_step(test_name, test_func)
        results.append((test_name, result))

        # Stop on first critical failure
        if not result and test_name in [
            "Configuration Loading",
            "DI Container Setup",
            "Domain Bootstrap Initialization",
        ]:
            print("\n❌ Critical test failed - stopping diagnostic")
            break

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ All tests passed - initialization should work correctly")
    else:
        print("\n❌ Some tests failed - please review the errors above")
        print("\nTroubleshooting tips:")
        print("1. Check hardware connections (LEDs, buttons)")
        print("2. Verify USE_MOCK_HARDWARE environment variable")
        print("3. Check GPIO permissions")
        print("4. Review system logs for hardware errors")


if __name__ == "__main__":
    asyncio.run(main())
