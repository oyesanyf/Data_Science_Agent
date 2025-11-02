#!/usr/bin/env python3
"""Update workflow to make list_data_files Step 1 and analyze_dataset Step 2."""
import re

# Read the agent.py file
with open('agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update STEP 1 section to include list_data_files first
old_step1 = '''STEP 1:  EXPLORATORY DATA ANALYSIS (EDA) - ALWAYS START HERE!
        "├─ analyze_dataset() → structure, preview'''

new_step1 = '''STEP 1:  FILE DISCOVERY - ALWAYS START HERE!
        "├─ list_data_files() → discover and list uploaded files FIRST
        "├─ analyze_dataset() → structure, preview (Step 2 after listing)'''

content = content.replace(old_step1, new_step1)

# Also update the STEP 2 section to move list_data_files from there if it exists
# Update any references to list_data_files in STEP 2 to clarify it's Step 1
old_step2_ref = '''STEP 2:  DATA CLEANING & PREPARATION
        "├─ Initial Assessment:
        "│  • list_data_files() → locate datasets
        "│  • analyze_dataset() → understand structure'''

new_step2_ref = '''STEP 2:  DATA CLEANING & PREPARATION
        "├─ Initial Assessment:
        "│  • analyze_dataset() → understand structure (should be done in Step 1 after list_data_files)'''

if old_step2_ref in content:
    content = content.replace(old_step2_ref, new_step2_ref)

# Write back
with open('agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated workflow: list_data_files is now Step 1, analyze_dataset is Step 2")

