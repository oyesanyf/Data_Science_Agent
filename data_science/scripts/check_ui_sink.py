#!/usr/bin/env python3
"""Check UI Sink database status"""
import sqlite3
from pathlib import Path

db_path = Path("data_science/adk_state.db")

if not db_path.exists():
    print("[X] Database not found")
    exit(1)

print("[OK] Database exists:", db_path)
print(f"   Size: {db_path.stat().st_size} bytes\n")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(" Tables in database:")
for table in tables:
    print(f"   - {table[0]}")

print()

# Count records in each table
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"   {table_name}: {count} records")

print()

# Show recent UI events
cursor.execute("SELECT COUNT(*) FROM ui_events")
ui_count = cursor.fetchone()[0]

if ui_count > 0:
    print(" Recent UI events:")
    cursor.execute("""
        SELECT session_id, tool_name, created_at 
        FROM ui_events 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    events = cursor.fetchall()
    for event in events:
        session_short = event[0][:12] if event[0] else "unknown"
        print(f"   {event[2]}: {event[1]} (session: {session_short}...)")
else:
    print("[WARNING]  No UI events recorded yet")
    print("   → This means no tools have successfully executed")

print()

# Show recent tool executions
cursor.execute("SELECT COUNT(*) FROM tool_executions")
tool_count = cursor.fetchone()[0]

if tool_count > 0:
    print(" Recent tool executions:")
    cursor.execute("""
        SELECT tool_name, success, duration_ms, executed_at 
        FROM tool_executions 
        ORDER BY executed_at DESC 
        LIMIT 10
    """)
    executions = cursor.fetchall()
    for exe in executions:
        status = "[OK]" if exe[1] else "[X]"
        print(f"   {status} {exe[0]} ({exe[2]:.0f}ms) at {exe[3]}")
else:
    print("[WARNING]  No tool executions recorded yet")

conn.close()

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)
if ui_count == 0 and tool_count == 0:
    print("[X] UI Sink is ready but no tools have executed successfully yet")
    print("   → Upload a file and run a tool to see UI output!")
else:
    print(f"[OK] UI Sink is working! {ui_count} events, {tool_count} executions")

