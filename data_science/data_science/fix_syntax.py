#!/usr/bin/env python3
"""Fix the syntax error in agent.py"""

# Read agent.py
with open('agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and fix the broken string literal
# The issue is that the string doesn't have proper line continuation
old_text = '''    "    When a user uploads a file, you MUST:
        "    1. Only acknowledge: 'File uploaded successfully.'
        "    2. DO NOT call ANY tools (list_data_files, analyze_dataset, etc.)
        "    3. DO NOT generate 'NEXT STEPS' or suggestions  
        "    4. WAIT for explicit user instruction
        "    ALL tools require explicit user request - NO EXCEPTIONS!'''

new_text = '''    "    When a user uploads a file, you MUST:\\n"
        "    1. Only acknowledge: 'File uploaded successfully.'\\n"
        "    2. DO NOT call ANY tools (list_data_files, analyze_dataset, etc.)\\n"
        "    3. DO NOT generate 'NEXT STEPS' or suggestions\\n"
        "    4. WAIT for explicit user instruction\\n"
        "    ALL tools require explicit user request - NO EXCEPTIONS!\\n"'''

if old_text in content:
    content = content.replace(old_text, new_text)
    print('Fixed syntax error: Added newline escapes')
else:
    print('ERROR: Could not find exact text to replace')
    # Try to show what's around line 3518
    lines = content.split('\n')
    if len(lines) > 3520:
        print(f'Line 3515: {repr(lines[3514])}')
        print(f'Line 3516: {repr(lines[3515])}')
        print(f'Line 3517: {repr(lines[3516])}')
        print(f'Line 3518: {repr(lines[3517])}')
        print(f'Line 3519: {repr(lines[3518])}')
        print(f'Line 3520: {repr(lines[3519])}')

# Write back
with open('agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')

