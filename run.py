#!/usr/bin/env python3
"""
Simple startup script for Hospital Bulk Processing API
Run this from the project root directory: python run.py
"""

import os
import sys
from pathlib import Path


def check_structure():
    """Verify project structure is correct"""
    current_dir = Path.cwd()
    app_dir = current_dir / "app"
    main_file = app_dir / "main.py"

    if not app_dir.exists():
        print(" Error: 'app' directory not found!")
        print(f"Current directory: {current_dir}")
        print("\nExpected structure:")
        print("  project-root/")
        print("    ├── app/")
        print("    │   ├── main.py")
        print("    │   ├── models.py")
        print("    │   ├── config.py")
        print("    │   └── services/")
        print("    ├── run.py (this file)")
        print("    └── requirements.txt")
        print("\nPlease ensure you're in the correct directory.")
        sys.exit(1)

    if not main_file.exists():
        print(" Error: 'app/main.py' not found!")
        print("Please ensure the application files are in the correct location.")
        sys.exit(1)

    print("✓ Project structure verified")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import httpx
        import pydantic
        print("✓ Required dependencies found")
        return True
    except ImportError as e:
        print(f" Missing dependency: {e}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


def main():
    """Main entry point"""
    print("=" * 50)
    print("Hospital Bulk Processing API")
    print("=" * 50)
    print()

    # Check project structure
    check_structure()

    # Check dependencies
    check_dependencies()

    # Add current directory to Python path
    current_dir = str(Path.cwd())
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    print()
    print("Starting server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    print()

    # Import and run uvicorn
    import uvicorn

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n Error starting server: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're in the project root directory")
        print("2. Verify all files are in place")
        print("3. Check that dependencies are installed")
        sys.exit(1)


if __name__ == "__main__":
    main()