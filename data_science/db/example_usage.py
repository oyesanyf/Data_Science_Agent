"""
Example Usage of DatabaseSessionService
========================================

Demonstrates how to use DatabaseSessionService in various scenarios.
"""

import asyncio
from datetime import datetime, timezone
from database_session_service import DatabaseSessionService, Session, Event

APP_NAME = "data_science_agent"
USER_ID = "user_123"
SESSION_ID = "sess_abc"


async def example_1_basic_usage():
    """Example 1: Basic session creation and state management."""
    print("\n" + "="*60)
    print("Example 1: Basic Usage")
    print("="*60)
    
    service = DatabaseSessionService()
    
    # Create session with initial state
    session = await service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={
            "user:preferred_model": "gpt-4",
            "dataset_path": "/data/train.csv",
            "theme": "dark",
            "temp:request_id": "req_xyz"  # Won't persist
        }
    )
    print(f"✓ Created session: {session.session_id}")
    
    # Retrieve session
    retrieved = await service.get_session(APP_NAME, USER_ID, SESSION_ID)
    print(f"✓ Retrieved session with {len(retrieved.state)} state keys:")
    for key, value in retrieved.state.items():
        if not key.startswith("temp:"):  # temp keys won't be in retrieved state
            print(f"  - {key}: {value}")


async def example_2_state_scoping():
    """Example 2: Demonstrating SESSION, USER, and APP scopes."""
    print("\n" + "="*60)
    print("Example 2: State Scoping")
    print("="*60)
    
    service = DatabaseSessionService()
    
    # Update with different scopes
    await service.update_keys(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        delta={
            # Session scope (only this session)
            "current_dataset": "train.csv",
            "progress": 0.75,
            
            # User scope (all sessions for this user)
            "user:preferred_language": "en",
            "user:models_trained": 5,
            
            # App scope (global across all users)
            "app:api_version": "2.0",
            "app:feature_flags": {"ml": True, "viz": True},
            
            # Temp scope (not persisted)
            "temp:trace_id": "xyz123"
        }
    )
    print("✓ Updated state with multiple scopes")
    
    # Retrieve and show scopes
    session = await service.get_session(APP_NAME, USER_ID, SESSION_ID)
    
    print("\nSession scope (no prefix):")
    for key, value in session.state.items():
        if not key.startswith(("user:", "app:", "temp:")):
            print(f"  - {key}: {value}")
    
    print("\nUser scope (user: prefix):")
    for key, value in session.state.items():
        if key.startswith("user:"):
            print(f"  - {key}: {value}")
    
    print("\nApp scope (app: prefix):")
    for key, value in session.state.items():
        if key.startswith("app:"):
            print(f"  - {key}: {value}")


async def example_3_event_logging():
    """Example 3: Appending events with state deltas."""
    print("\n" + "="*60)
    print("Example 3: Event Logging")
    print("="*60)
    
    service = DatabaseSessionService()
    session = await service.get_session(APP_NAME, USER_ID, SESSION_ID)
    
    # Append event for model training
    event1 = Event(
        invocation_id="train_model_1",
        author="agent",
        timestamp=datetime.now(timezone.utc).timestamp(),
        content={"tool": "train_classifier", "model": "random_forest"},
        actions=type('obj', (object,), {
            'state_delta': {
                "model_trained": True,
                "model_path": "/models/rf_classifier.pkl",
                "model_accuracy": 0.95,
                "user:total_models": 6  # Increment user counter
            }
        })()
    )
    await service.append_event(session, event1)
    print("✓ Appended training event")
    
    # Append event for prediction
    event2 = Event(
        invocation_id="predict_1",
        author="agent",
        timestamp=datetime.now(timezone.utc).timestamp(),
        content={"tool": "predict", "num_samples": 100},
        actions=type('obj', (object,), {
            'state_delta': {
                "last_prediction": "2025-01-10T14:30:00",
                "predictions_count": 100
            }
        })()
    )
    await service.append_event(session, event2)
    print("✓ Appended prediction event")
    
    # Get event count
    count = service.get_event_count(APP_NAME, USER_ID, SESSION_ID)
    print(f"✓ Total events: {count}")


async def example_4_deletion():
    """Example 4: Deleting state keys."""
    print("\n" + "="*60)
    print("Example 4: State Deletion")
    print("="*60)
    
    service = DatabaseSessionService()
    
    # Set some temporary keys
    await service.update_keys(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        delta={
            "temp_key1": "will be deleted",
            "temp_key2": "also deleted",
            "keep_this": "permanent"
        }
    )
    print("✓ Created temp keys")
    
    session = await service.get_session(APP_NAME, USER_ID, SESSION_ID)
    print(f"State before deletion: {len(session.state)} keys")
    
    # Delete keys by setting to None
    await service.update_keys(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        delta={
            "temp_key1": None,  # DELETE
            "temp_key2": None,  # DELETE
            "keep_this": "still here"  # UPDATE
        }
    )
    print("✓ Deleted temp keys")
    
    session = await service.get_session(APP_NAME, USER_ID, SESSION_ID)
    print(f"State after deletion: {len(session.state)} keys")


async def example_5_listing_sessions():
    """Example 5: Listing sessions."""
    print("\n" + "="*60)
    print("Example 5: Listing Sessions")
    print("="*60)
    
    service = DatabaseSessionService()
    
    # Create a few more sessions
    await service.create_session(APP_NAME, USER_ID, "sess_xyz", state={"test": 1})
    await service.create_session(APP_NAME, USER_ID, "sess_123", state={"test": 2})
    print("✓ Created additional sessions")
    
    # List all sessions for this user
    sessions = await service.list_sessions(app_name=APP_NAME, user_id=USER_ID)
    print(f"\n✓ Found {len(sessions)} sessions for {USER_ID}:")
    for sess in sessions:
        print(f"  - {sess['session_id']} (updated: {sess['updated_at']})")


async def example_6_statistics():
    """Example 6: Database statistics."""
    print("\n" + "="*60)
    print("Example 6: Database Statistics")
    print("="*60)
    
    service = DatabaseSessionService()
    
    stats = service.get_stats()
    print("Database Statistics:")
    print(f"  - Sessions: {stats['sessions']}")
    print(f"  - Events: {stats['events']}")
    print(f"  - State Keys: {stats['state_keys']}")
    print(f"  - DB Size: {stats['db_size_mb']:.2f} MB")


async def example_7_cleanup():
    """Example 7: Session deletion and database maintenance."""
    print("\n" + "="*60)
    print("Example 7: Cleanup")
    print("="*60)
    
    service = DatabaseSessionService()
    
    # Delete old session
    await service.delete_session(APP_NAME, USER_ID, "sess_xyz")
    print("✓ Deleted session: sess_xyz")
    
    # Vacuum database
    service.vacuum()
    print("✓ Database vacuumed (maintenance complete)")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("DatabaseSessionService - Example Usage")
    print("="*60)
    
    try:
        await example_1_basic_usage()
        await example_2_state_scoping()
        await example_3_event_logging()
        await example_4_deletion()
        await example_5_listing_sessions()
        await example_6_statistics()
        await example_7_cleanup()
        
        print("\n" + "="*60)
        print("✓ All examples completed successfully!")
        print("="*60)
        print(f"\nDatabase location: data_science/db/adk.sqlite3")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

