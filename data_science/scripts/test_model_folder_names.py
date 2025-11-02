#!/usr/bin/env python3
"""
Test model folder name extraction from uploaded filenames.
"""

import re
import os

def extract_original_name(filename):
    """Extract original filename from uploaded file."""
    # Get filename without extension
    name = os.path.splitext(os.path.basename(filename))[0]
    
    # Strip timestamp prefixes added by file upload system
    # Pattern 1: "uploaded_<timestamp>_<original_name>"
    name = re.sub(r'^uploaded_\d+_', '', name)
    
    # Pattern 2: "<timestamp>_<original_name>" (if uploaded_ was already removed)
    name = re.sub(r'^\d{10,}_', '', name)
    
    # If name is still empty after stripping, use the full original name
    if not name:
        name = os.path.splitext(os.path.basename(filename))[0]
    
    # Sanitize dataset name (remove special characters)
    name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    
    return name

# Test cases
test_cases = [
    # Format: (input_filename, expected_output)
    ("uploaded_1760564375_customer_data.csv", "customer_data"),
    ("uploaded_1760578142_sales_report.csv", "sales_report"),
    ("1760564375_customer_data.csv", "customer_data"),
    ("customer_data_cleaned.csv", "customer_data_cleaned"),
    ("data.csv", "data"),
    ("my-dataset.csv", "my-dataset"),
    ("test_file_123.csv", "test_file_123"),
    (".uploaded/uploaded_1760564375_customer_data.csv", "customer_data"),
    ("C:\\harfile\\data_science_agent\\data_science\\.uploaded\\uploaded_1760564375_customer_data.csv", "customer_data"),
    ("selected_kbest.csv", "selected_kbest"),
]

print("=" * 70)
print("TESTING MODEL FOLDER NAME EXTRACTION")
print("=" * 70)
print()

passed = 0
failed = 0

for input_file, expected in test_cases:
    result = extract_original_name(input_file)
    status = "[OK]" if result == expected else "[FAIL]"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} {input_file}")
    print(f"     Expected: {expected}")
    print(f"     Got:      {result}")
    if result != expected:
        print(f"     ^^^ MISMATCH!")
    print()

print("=" * 70)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 70)

if failed > 0:
    exit(1)
else:
    print("\n[OK] ALL TESTS PASSED!")

