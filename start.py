#!/usr/bin/env python3
"""
Startup script for Hiya Sales Agent MVP
Starts both FastAPI server and Streamlit UI
"""

import subprocess
import sys
import time
import os
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import streamlit
        import uvicorn
        print("OK All dependencies are installed")
        return True
    except ImportError as e:
        print(f"X Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False


def start_fastapi():
    """Start FastAPI server"""
    print("Starting FastAPI server...")
    try:
        subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "frontend.app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"
        ])
        print("OK FastAPI server started on http://localhost:8000")
        return True
    except Exception as e:
        print(f"X Failed to start FastAPI server: {e}")
        return False


def start_streamlit():
    """Start Streamlit UI"""
    print("Starting Streamlit UI...")
    try:
        subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py",
            "--server.port", "8501", "--server.address", "0.0.0.0"
        ])
        print("OK Streamlit UI started on http://localhost:8501")
        print("   • Main page: http://localhost:8501")
        print("   • Voice Agent: http://localhost:8501/Voice_Agent")
        return True
    except Exception as e:
        print(f"X Failed to start Streamlit UI: {e}")
        return False


def main():
    """Main startup function"""
    print("Hiya Sales Agent MVP Startup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("frontend/app/main.py").exists():
        print("X Please run this script from the project root directory")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check for .env file
    if not Path(".env").exists():
        print("WARNING: No .env file found. Creating from template...")
        env_content = """OPENAI_API_KEY=your_key_here
GOOGLE_CREDENTIALS_PATH=./google_credentials.json
GOOGLE_CALENDAR_ID=primary
TZ=America/New_York
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print("OK Created .env file")
    
    # Start services
    print("\nStarting services...")
    
    fastapi_started = start_fastapi()
    if not fastapi_started:
        sys.exit(1)
    
    # Wait a moment for FastAPI to start
    time.sleep(2)
    
    streamlit_started = start_streamlit()
    if not streamlit_started:
        sys.exit(1)
    
    print("\nSUCCESS: All services started successfully!")
    print("\nAccess the application:")
    print("   • Streamlit UI: http://localhost:8501")
    print("   • FastAPI docs: http://localhost:8000/docs")
    print("   • Health check: http://localhost:8000/health")
    
    print("\nTips:")
    print("   • Add leads in the Streamlit sidebar")
    print("   • Start calls by clicking 'Start Call'")
    print("   • Try responses like 'Yes, I'm interested' or 'I'm busy'")
    
    print("\nTo stop: Press Ctrl+C")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
