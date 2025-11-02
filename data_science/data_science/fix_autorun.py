#!/usr/bin/env python3
"""Fix auto-run issues by disabling callbacks and updating prompts."""
import re

# Read agent.py
with open('agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Comment out the after_upload_callback call
content = content.replace(
    'after_upload_callback(tool_context=callback_context, result=upload_result)',
    '# DISABLED: after_upload_callback(tool_context=callback_context, result=upload_result)'
)

# Fix the garbled system prompt
old_text = 'Only acknowledge the upload and wait for explicit user instructions., then analyze_dataset() as Step 2.'
new_text = 'Only acknowledge the upload with: "File uploaded successfully." DO NOT call any tools. DO NOT generate suggestions. WAIT for explicit user instruction.'
content = content.replace(old_text, new_text)

# Write back
with open('agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed auto-run issues")

