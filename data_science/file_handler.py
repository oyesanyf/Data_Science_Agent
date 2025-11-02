"""
File handler to save uploaded files and keep them out of token context.
This prevents CSV data from counting against the 1M token limit.
"""

import os
from pathlib import Path
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any


class FileHandler:
    """Handle file uploads by saving to disk and returning only paths."""
    
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    def save_upload(self, content: bytes, filename: str = None) -> str:
        """
        Save uploaded content to disk and return the file path.
        
        Args:
            content: File content as bytes
            filename: Optional filename, auto-generated if not provided
        
        Returns:
            Path to saved file
        """
        if filename is None:
            # Generate filename from content hash + timestamp
            content_hash = hashlib.md5(content).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_{timestamp}_{content_hash}.csv"
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        # Save file
        filepath = self.upload_dir / filename
        with open(filepath, 'wb') as f:
            f.write(content)
        
        return str(filepath)
    
    def save_text(self, text: str, filename: str = None, extension: str = ".csv") -> str:
        """
        Save text content to disk.
        
        Args:
            text: Text content
            filename: Optional filename
            extension: File extension (default .csv)
        
        Returns:
            Path to saved file
        """
        return self.save_upload(text.encode('utf-8'), filename or f"data{extension}")
    
    def list_uploads(self) -> list:
        """List all uploaded files."""
        return [str(f) for f in self.upload_dir.glob("*")]
    
    def cleanup_old_files(self, days: int = 7):
        """Remove files older than specified days."""
        import time
        now = time.time()
        for f in self.upload_dir.glob("*"):
            if now - f.stat().st_mtime > days * 86400:
                f.unlink()
    
    def save_and_analyze(self, content: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Save file and return token-safe metadata.
        
        Args:
            content: File content
            filename: Optional filename
        
        Returns:
            Dictionary with file path and metadata
        """
        # Save file
        file_path = self.save_upload(content, filename)
        
        # Get token-safe reference
        from data_science.chunking_utils import get_safe_csv_reference
        try:
            return get_safe_csv_reference(file_path)
        except Exception as e:
            return {
                "file_path": file_path,
                "error": str(e),
                "message": "File saved, but could not analyze"
            }


# Global file handler instance
file_handler = FileHandler()

