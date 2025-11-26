#!/usr/bin/env python3
"""
Test script to verify application shutdown behavior specifically for graceful shutdown.
"""

import os
import sys
import signal
import subprocess
import time
import pytest

def test_graceful_shutdown():
    """Test the application graceful shutdown to verify background tasks stop properly."""
    print("🚀 Testing TheOpenMusicBox graceful shutdown...")
    
    # Set test environment variables
    os.environ['USE_MOCK_HARDWARE'] = 'true'
    
    print("📝 Starting application...")
    process = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 
        'app.main:app_sio',
        '--host', '127.0.0.1',
        '--port', '5005'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    try:
        # Let it start up completely
        print("⏳ Waiting 5 seconds for complete startup...")
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ ERROR: Process exited during startup with code {process.returncode}")
            print("📝 Startup output:")
            print(stderr[-2000:])  # Last 2000 chars
            pytest.fail(f"Process exited during startup with code {process.returncode}")
        
        print("✅ Application started successfully")
        
        # Send SIGTERM (graceful shutdown)
        print("📡 Sending SIGTERM for graceful shutdown...")
        shutdown_start = time.time()
        process.send_signal(signal.SIGTERM)
        
        # Wait for shutdown with timeout
        print("⏳ Waiting for graceful shutdown (max 15 seconds)...")
        try:
            stdout, stderr = process.communicate(timeout=15)
            shutdown_time = time.time() - shutdown_start
            
            if process.returncode == 0:
                print(f"✅ SUCCESS: Application shut down gracefully in {shutdown_time:.2f} seconds")
                print("📝 Shutdown log lines:")
                for line in stderr.split('\n')[-15:]:
                    if line.strip() and ('shutdown' in line.lower() or 'cleanup' in line.lower() or 'stopped' in line.lower()):
                        print(f"  {line}")
                # Test passed
            else:
                print(f"⚠️ WARNING: Application exited with code {process.returncode} after {shutdown_time:.2f}s")
                print("📝 Last few log lines:")
                for line in stderr.split('\n')[-10:]:
                    if line.strip():
                        print(f"  {line}")
                pytest.fail(f"Application exited with code {process.returncode}")
                
        except subprocess.TimeoutExpired:
            shutdown_time = time.time() - shutdown_start
            print(f"❌ TIMEOUT: Application did not shut down within 15 seconds (waited {shutdown_time:.2f}s)")
            
            # Try to get some output before killing
            try:
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                
            print("📝 Process was stuck - had to kill it. Last few log lines:")
            for line in stderr.split('\n')[-15:]:
                if line.strip():
                    print(f"  {line}")
            pytest.fail("Application did not shut down within 15 seconds")

    except Exception as e:
        print(f"💥 Exception during shutdown test: {e}")
        process.kill()
        pytest.fail(f"Exception during shutdown test: {e}")

if __name__ == "__main__":
    try:
        test_graceful_shutdown()
        sys.exit(0)
    except (AssertionError, Exception):
        sys.exit(1)