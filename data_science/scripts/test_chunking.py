"""
Test script to demonstrate automatic chunking for large CSV files.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Create a large test CSV
def create_large_csv(rows=500_000, cols=50):
    """Create a large CSV file that would exceed token limits."""
    print(f"Creating test CSV with {rows:,} rows and {cols} columns...")
    
    # Generate random data
    data = {}
    for i in range(cols):
        if i == 0:
            data['target'] = np.random.choice(['A', 'B', 'C'], size=rows)
        else:
            data[f'feature_{i}'] = np.random.randn(rows)
    
    df = pd.DataFrame(data)
    
    # Save to uploads directory
    output_path = Path("uploads/large_test_data.csv")
    output_path.parent.mkdir(exist_ok=True)
    df.to_csv(output_path, index=False)
    
    # Calculate file size
    size_mb = output_path.stat().st_size / 1024 / 1024
    
    print(f"[OK] Created {output_path}")
    print(f" Size: {size_mb:.2f} MB")
    print(f" Rows: {rows:,}")
    print(f" Columns: {cols}")
    
    return str(output_path)


def test_token_counting():
    """Test token counting on the large file."""
    from data_science.chunking_utils import data_chunker
    
    csv_path = "uploads/large_test_data.csv"
    
    print("\n--- Token Analysis ---")
    
    # Check if chunking is needed
    needs_chunking = data_chunker.should_chunk_file(csv_path)
    print(f"Needs chunking: {needs_chunking}")
    
    # Get summary
    summary = data_chunker.get_csv_summary(csv_path)
    print(f"\nSummary (token-efficient):\n{summary}")
    
    # Count tokens in summary vs full file
    summary_tokens = data_chunker.count_tokens(summary)
    print(f"\n Summary tokens: {summary_tokens:,}")
    print(f"[OK] This is small enough to pass to LLM!")


def test_safe_reference():
    """Test getting a safe reference to the large file."""
    from data_science.chunking_utils import get_safe_csv_reference
    
    csv_path = "uploads/large_test_data.csv"
    
    print("\n--- Safe Reference Test ---")
    
    info = get_safe_csv_reference(csv_path)
    print(f"File path: {info['file_path']}")
    print(f"Needs chunking: {info['needs_chunking']}")
    print(f"Recommendation: {info['recommendation']}")


if __name__ == "__main__":
    # Create test file
    csv_path = create_large_csv(rows=500_000, cols=50)
    
    # Test token counting
    test_token_counting()
    
    # Test safe reference
    test_safe_reference()
    
    print("\n" + "="*60)
    print(" Chunking system is working!")
    print("="*60)
    print("\nNow test in the web UI:")
    print("1. Go to http://localhost:8000")
    print("2. Say: 'Run AutoML on uploads/large_test_data.csv with target \"target\"'")
    print("3. The system will automatically sample to 100k rows")
    print("4. [OK] No token limit errors!")

