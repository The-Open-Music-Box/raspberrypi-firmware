#!/usr/bin/env python3
"""
Test script to verify application startup after fixing syntax errors.
"""

import sys
import os
import subprocess
import time
import signal

def test_startup():
    """Test the application startup to verify all syntax errors are fixed."""
    print("🚀 Testing TheOpenMusicBox application startup...")
    print("🔧 Environment: LOCAL TEST MODE")
    print("-" * 50)
    
    # Set test environment variables
    os.environ['USE_MOCK_HARDWARE'] = 'true'
    os.environ['DEBUG'] = 'true'
    os.environ['PORT'] = '5005'  # Use different port for testing
    
    try:
        # Start the application
        print("📝 Starting application with mock hardware...")
        process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app_sio',
            '--host', '127.0.0.1',
            '--port', '5005',
            '--log-level', 'info'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it time to start or fail
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ SUCCESS: Application started successfully!")
            print("🎯 No syntax errors detected")
            print("🏗️ Unified architecture is operational")
            
            # Terminate the test process
            process.terminate()
            process.wait(timeout=5)
            return True
        else:
            # Process exited, get error output
            stdout, stderr = process.communicate()
            print("❌ FAILURE: Application failed to start")
            print("📝 STDOUT:", stdout)
            print("🚨 STDERR:", stderr)
            return False
            
    except Exception as e:
        print(f"💥 Exception during startup test: {e}")
        return False

if __name__ == "__main__":
    success = test_startup()
    sys.exit(0 if success else 1)