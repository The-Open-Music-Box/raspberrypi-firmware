#!/usr/bin/env python
"""Production starter script that explicitly uses StandardConfig.

This script starts the application in production mode with real hardware.
"""
import sys
from pathlib import Path

import uvicorn

from app.src.config.config_factory import ConfigFactory, ConfigType

# Ensure app directory is in path
sys.path.append(str(Path(__file__).resolve().parent))

# Force stdout to be unbuffered
sys.stdout.reconfigure(line_buffering=True)


print("[TheOpenMusicBox] Starting application in PRODUCTION mode")

# Get production configuration
config = ConfigFactory.create_config(ConfigType.PRODUCTION)

if config.hardware.mock_hardware:
    print("[TheOpenMusicBox] WARNING: Mock hardware is enabled in production!")
else:
    print("[TheOpenMusicBox] Using REAL hardware")

try:
    # Display complete configuration info
    hw_mode = "REAL" if not config.hardware.mock_hardware else "MOCK"
    print("[TheOpenMusicBox] Configuration details:")
    print(f"  - App module: {config.app_module}")
    print(f"  - Host: {config.socketio_host}")
    print(f"  - Port: {config.socketio_port}")
    print(f"  - Hardware mode: {hw_mode}")
    print(f"  - Debug mode: {config.debug}")
    print(f"  - Auto reload: {config.uvicorn_reload}")
    print(f"  - Upload folder: {config.upload_folder}")
    print(f"  - Database file: {config.db_file}")

    print("[TheOpenMusicBox] Starting ASGI server...")
    sys.stdout.flush()

    # Start the ASGI server
    uvicorn.run(
        config.app_module,
        host=config.socketio_host,
        port=config.socketio_port,
        reload=config.uvicorn_reload,
        factory=False,
    )

except KeyboardInterrupt:
    print("\n[TheOpenMusicBox] Received shutdown signal, exiting...")
    sys.exit(0)
except Exception as e:
    print(f"[TheOpenMusicBox] Error: {e}")
    sys.exit(1)
