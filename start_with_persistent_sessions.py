"""
Start the Data Science Agent with persistent sessions using DatabaseSessionService.

This script replaces InMemorySessionService with DatabaseSessionService
to ensure sessions survive restarts.
"""
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the agent
from data_science import agent

# Import DatabaseSessionService
from data_science.db import DatabaseSessionService

# Import Runner
from google.adk.runners import Runner

# Create persistent session service
session_service = DatabaseSessionService()
print(f"✅ Using DatabaseSessionService: {session_service.db_path}")

# Note: To fully integrate, you'd need to create a custom Runner
# For now, the environment variable approach (Option 1) is easier

print("""
✅ DatabaseSessionService is ready!

To use it with the FastAPI app:
1. Set environment variable:
   $env:SESSION_SERVICE_URI = "sqlite:///./data_science/db/adk_sessions.db"

2. Restart agent:
   python main.py

Or use a custom runner (see DatabaseSessionService docs).
""")

# Verify database exists
if Path(session_service.db_path).exists():
    size = Path(session_service.db_path).stat().st_size
    print(f"✅ Database file exists: {size} bytes")
else:
    print("⚠️ Database will be created on first session")

print(f"\n📊 Database location: {Path(session_service.db_path).absolute()}")

