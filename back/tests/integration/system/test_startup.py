#!/usr/bin/env python3
"""
Test script to verify application startup after fixing syntax errors.
"""

import sys
import os
import subprocess
import time
import signal
import socket
import pytest


def get_free_port():
    """Get a free port by letting the OS assign one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    # Small delay to ensure OS releases the port
    time.sleep(0.1)
    return port


def cleanup_orphaned_processes(port):
    """Kill any orphaned uvicorn processes on the test port."""
    try:
        subprocess.run(
            ['pkill', '-f', f'uvicorn.*{port}'],
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        time.sleep(1)  # Wait for OS to release port
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # pkill not available or no processes found


def test_startup():
    """Test the application startup to verify all syntax errors are fixed."""
    print("🚀 Testing TheOpenMusicBox application startup...")
    print("🔧 Environment: LOCAL TEST MODE")
    print("-" * 50)

    # Get a free port dynamically
    port = get_free_port()
    print(f"🔌 Using dynamic port: {port}")

    # Clean up any orphaned processes
    cleanup_orphaned_processes(port)

    # Set test environment variables
    os.environ['USE_MOCK_HARDWARE'] = 'true'
    os.environ['DEBUG'] = 'true'
    os.environ['PORT'] = str(port)

    process = None
    try:
        # Start the application
        print("📝 Starting application with mock hardware...")
        process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn',
            'app.main:app_sio',
            '--host', '127.0.0.1',
            '--port', str(port),
            '--log-level', 'info'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Give it time to start or fail
        time.sleep(5)

        # Check if process is still running
        if process.poll() is None:
            print("✅ SUCCESS: Application started successfully!")
            print("🎯 No syntax errors detected")
            print("🏗️ Unified architecture is operational")
            # Test passed
        else:
            # Process exited, get error output
            stdout, stderr = process.communicate()
            print("❌ FAILURE: Application failed to start")
            print("📝 STDOUT:", stdout)
            print("🚨 STDERR:", stderr)
            pytest.fail(f"Application failed to start with code {process.returncode}")

    except Exception as e:
        print(f"💥 Exception during startup test: {e}")
        pytest.fail(f"Exception during startup test: {e}")

    finally:
        # Ensure cleanup happens even if test fails
        if process is not None:
            try:
                if process.poll() is None:
                    print("🧹 Cleaning up test process...")
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                        print("✅ Process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        print("⚠️ Process didn't terminate, forcing kill...")
                        process.kill()
                        process.wait()
                        print("✅ Process killed")
            except Exception as cleanup_error:
                print(f"⚠️ Error during cleanup: {cleanup_error}")

if __name__ == "__main__":
    try:
        test_startup()
        sys.exit(0)
    except (AssertionError, Exception):
        sys.exit(1)