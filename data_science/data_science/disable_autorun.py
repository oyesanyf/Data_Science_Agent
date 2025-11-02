#!/usr/bin/env python3
"""Completely disable all auto-runs after file upload."""
import re

# Read agent.py
with open('agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the entire after_upload_callback block
pattern = r'\s*# CRITICAL FIX: Trigger the after_upload_callback.*?\n\s*logger\.error\(f"\[UPLOAD_CALLBACK\] FAILED.*?\)'
content = re.sub(pattern, '', content, flags=re.DOTALL)

# Strengthen the no-auto rule in system prompt
old_rule = r'⚠️\s*IMPORTANT: NO tools run automatically after upload\.\n.*?When a user uploads a file.*?analyze_dataset\(\) as Step 2\.'
new_rule = '''⚠️  CRITICAL RULE: ABSOLUTELY NO tools run automatically after upload.
        "    When a user uploads a file, you MUST:
        "    1. Acknowledge the upload with ONLY: "File uploaded successfully."
        "    2. DO NOT call ANY tools (list_data_files, analyze_dataset, etc.)
        "    3. DO NOT generate "NEXT STEPS" or suggestions
        "    4. DO NOT provide recommendations
        "    5. WAIT for explicit user instruction before doing anything else
        "    ALL tools require explicit user request - NO EXCEPTIONS!'''

content = re.sub(old_rule, new_rule, content, flags=re.DOTALL)

# Write back
with open('agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Disabled all auto-runs and strengthened no-auto rule")

