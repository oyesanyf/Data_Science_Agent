"""
Token-aware chunking for large CSV files to prevent Gemini API token limit errors.
Automatically splits large files and processes them in manageable chunks.
"""

import os
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
import google.genai as genai


class DataChunker:
    """Handles chunking of large CSV files to stay within token limits."""
    
    # Gemini 1.5/2.0 limits
    MAX_TOKENS = 1_000_000  # Conservative limit (actual is 1,048,575)
    SAFE_CHUNK_TOKENS = 900_000  # Leave headroom for instructions/tools
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        try:
            self.client = genai.Client()
        except Exception:
            self.client = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's native API."""
        if not self.client:
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4
        
        try:
            result = self.client.models.count_tokens(
                model=self.model,
                contents=text
            )
            return result.total_tokens
        except Exception:
            # Fallback
            return len(text) // 4
    
    def should_chunk_file(self, file_path: str) -> bool:
        """Check if file is too large and needs chunking."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(1_000_000)  # Read first 1MB
            
            # Extrapolate token count
            file_size = os.path.getsize(file_path)
            sample_tokens = self.count_tokens(sample)
            estimated_total = (sample_tokens / len(sample)) * file_size
            
            return estimated_total > self.SAFE_CHUNK_TOKENS
        except Exception:
            return False
    
    def chunk_csv_by_rows(
        self,
        csv_path: str,
        output_dir: Optional[str] = None
    ) -> List[str]:
        """
        Split large CSV into smaller chunk files by rows.
        
        Args:
            csv_path: Path to large CSV file
            output_dir: Directory to save chunks (default: same as source)
        
        Returns:
            List of chunk file paths
        """
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        
        # Estimate rows per chunk to stay under token limit
        sample_csv = df.head(100).to_csv(index=False)
        sample_tokens = self.count_tokens(sample_csv)
        tokens_per_row = sample_tokens / 100
        
        # Conservative chunk size
        rows_per_chunk = int(self.SAFE_CHUNK_TOKENS / tokens_per_row * 0.8)
        rows_per_chunk = max(100, min(rows_per_chunk, 50000))  # 100-50k rows
        
        # Create output directory
        if output_dir is None:
            output_dir = Path(csv_path).parent / "chunks"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Split into chunks
        chunk_paths = []
        base_name = Path(csv_path).stem
        
        for i in range(0, total_rows, rows_per_chunk):
            chunk_df = df.iloc[i:i + rows_per_chunk]
            chunk_path = output_dir / f"{base_name}_chunk_{i//rows_per_chunk + 1}.csv"
            chunk_df.to_csv(chunk_path, index=False)
            chunk_paths.append(str(chunk_path))
        
        print(f"[OK] Split {csv_path} into {len(chunk_paths)} chunks")
        print(f" Chunks saved to: {output_dir}")
        return chunk_paths
    
    def chunk_text_content(
        self,
        text: str,
        max_tokens: int = 30000
    ) -> List[str]:
        """
        Split text into token-safe chunks for description/analysis.
        
        Args:
            text: Text content to chunk
            max_tokens: Maximum tokens per chunk
        
        Returns:
            List of text chunks
        """
        # Create character-based chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        initial_chunks = splitter.split_text(text)
        
        # Filter by token count
        final_chunks = []
        for chunk in initial_chunks:
            tokens = self.count_tokens(chunk)
            if tokens <= max_tokens:
                final_chunks.append(chunk)
            else:
                # Re-chunk tighter if necessary
                inner_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=2000,
                    chunk_overlap=100
                )
                for inner_chunk in inner_splitter.split_text(chunk):
                    if self.count_tokens(inner_chunk) <= max_tokens:
                        final_chunks.append(inner_chunk)
        
        return final_chunks
    
    def get_csv_summary(self, csv_path: str) -> str:
        """
        Get token-efficient summary of CSV file.
        
        Returns:
            Compact summary string describing the CSV
        """
        df = pd.read_csv(csv_path)
        
        summary = f"""CSV File: {Path(csv_path).name}
Rows: {len(df):,} | Columns: {len(df.columns)}
Columns: {', '.join(df.columns[:20])}{'...' if len(df.columns) > 20 else ''}

Data Types:
{df.dtypes.value_counts().to_string()}

Missing Values:
{df.isnull().sum()[df.isnull().sum() > 0].to_string()}

Sample (first 3 rows):
{df.head(3).to_string()}"""
        
        return summary


# Global instance
data_chunker = DataChunker()


def auto_chunk_if_needed(csv_path: str) -> List[str]:
    """
    Automatically chunk file if it's too large.
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        List of file paths (original if small, chunks if large)
    """
    if data_chunker.should_chunk_file(csv_path):
        print(f"[WARNING] File {csv_path} is too large, chunking...")
        return data_chunker.chunk_csv_by_rows(csv_path)
    else:
        return [csv_path]


def get_safe_csv_reference(csv_path: str) -> Dict[str, Any]:
    """
    Get token-safe reference to CSV file.
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        Dictionary with file info and whether chunking is needed
    """
    needs_chunking = data_chunker.should_chunk_file(csv_path)
    
    return {
        "file_path": csv_path,
        "needs_chunking": needs_chunking,
        "summary": data_chunker.get_csv_summary(csv_path),
        "recommendation": (
            "File is large. Process in chunks or use direct file path."
            if needs_chunking
            else "File is small enough to process directly."
        )
    }

