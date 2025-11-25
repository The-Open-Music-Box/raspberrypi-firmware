# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Hardware initialization retry helper.

This module provides a reusable retry mechanism for hardware initialization
that may fail on first boot due to timing or hardware readiness issues.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_hardware_init(
    name: str,
    init_func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    retry_delay: float = 2.0,
    critical: bool = False
) -> tuple[bool, T | None]:
    """Generic hardware initialization with retry logic.

    Args:
        name: Hardware component name for logging (e.g., "LED system")
        init_func: Async function to call for initialization
        max_retries: Maximum retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 2.0)
        critical: If True, raise exception on failure; if False, log and continue

    Returns:
        Tuple of (success: bool, result: T | None)
        - (True, result) if initialization succeeded
        - (False, None) if non-critical initialization failed
        - Raises exception if critical initialization failed

    Raises:
        Exception: If critical=True and all retry attempts fail

    Example:
        >>> async def init_led():
        ...     await led_manager.initialize()
        ...     return led_manager
        >>> success, led = await retry_hardware_init("LED system", init_led)
        >>> if success:
        ...     print(f"LED initialized: {led}")
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🔄 Initializing {name} (attempt {attempt}/{max_retries})...")
            result = await init_func()
            logger.info(f"✅ {name} initialized successfully")
            return (True, result)

        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"⚠️ {name} initialization attempt {attempt}/{max_retries} failed: {e}"
                )
                logger.info(
                    f"🔄 Retrying in {retry_delay}s... (hardware may not be ready yet)"
                )
                await asyncio.sleep(retry_delay)
            else:
                error_msg = f"❌ {name} failed after {max_retries} attempts: {e}"

                if critical:
                    logger.error(error_msg, exc_info=True)
                    raise RuntimeError(
                        f"Critical hardware initialization failed: {name}"
                    ) from e
                logger.error(error_msg, exc_info=True)
                logger.warning(
                    f"⚠️ Continuing without {name} (non-critical component)"
                )
                return (False, None)

    # Should never reach here, but satisfy type checker
    return (False, None)
