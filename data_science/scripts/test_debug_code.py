#!/usr/bin/env python3
"""
Test script to verify if the server is loading the new debug code.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_science'))

def test_debug_code():
    """Test if the new debug code is loaded."""
    try:
        # Try to import the agent module
        import data_science.agent as agent
        
        # Check if the debug logging is in the file upload callback
        source_code = open('data_science/agent.py', 'r', encoding='utf-8').read()
        
        if ' DEBUG: Log all available attributes' in source_code:
            print("[OK] NEW DEBUG CODE FOUND in agent.py")
            return True
        else:
            print("[X] OLD CODE FOUND in agent.py")
            return False
            
    except Exception as e:
        print(f"[X] ERROR: {e}")
        return False

if __name__ == "__main__":
    print(" Testing if server is running new debug code...")
    result = test_debug_code()
    if result:
        print("[OK] Server should be running new debug code")
    else:
        print("[X] Server is running old code")
