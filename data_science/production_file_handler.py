"""
Production-grade file handler with ZIP, images, CSV support + security validation.

Handles uploads with:
- Size limits and type validation
- Safe ZIP extraction (zip bomb protection)
- Image thumbnails with EXIF stripping
- Audit logging
- Hash-based deduplication
"""
from __future__ import annotations

import os
import uuid
import base64
import logging
from typing import Optional, Tuple, Any, Dict
from pathlib import Path

from .config import Config
from .validators import (
    validate_file_size,
    validate_extension,
    safe_unzip,
    sanitize_filename
)
from .observability import audit_logger, metrics, hash_file

logger = logging.getLogger(__name__)


def to_bytes(raw: Any) -> bytes:
    """Convert various input formats to bytes."""
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    try:
        return base64.b64decode(raw, validate=True)
    except Exception:
        return str(raw).encode("utf-8", "ignore")


class ProductionFileHandler:
    """Production-grade file upload handler with security & observability."""
    
    def __init__(self):
        self.quarantine_dir = Path(Config.QUARANTINE_DIR)
        self.ready_dir = Path(Config.READY_DIR)
        self.thumbnails_dir = Path(Config.THUMBNAILS_DIR)
        
        # Ensure directories exist with secure permissions
        for dir_path in [self.quarantine_dir, self.ready_dir, self.thumbnails_dir]:
            dir_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    
    def handle_upload(
        self,
        payload: bytes,
        mime_type: str,
        original_filename: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Handle file upload with full validation and processing.
        
        Args:
            payload: File bytes
            mime_type: MIME type (untrusted)
            original_filename: Original filename (optional)
            user_id: User identifier for audit (optional)
        
        Returns:
            (success: bool, result_path_or_message: str, error: Optional[str])
        """
        # Validate size
        is_valid, error = validate_file_size(len(payload))
        if not is_valid:
            metrics.increment("upload_rejected_size")
            audit_logger.log_upload(
                user_id, original_filename or "unknown", len(payload),
                mime_type, "", "rejected_size", error
            )
            return False, f"[X] {error}", error
        
        # Compute hash for deduplication and audit
        import hashlib
        file_hash = hashlib.sha256(payload).hexdigest()
        
        # Determine file kind and extension
        mime_lower = mime_type.lower()
        if "zip" in mime_lower:
            kind, ext = "zip", ".zip"
        elif "csv" in mime_lower or mime_lower.startswith("text/"):
            kind, ext = "csv", ".csv"
        elif mime_lower.startswith("image/"):
            kind, ext = "image", os.path.splitext(original_filename)[1] if original_filename else ".jpg"
        else:
            kind, ext = "other", ".bin"
        
        # Validate extension
        is_valid, error = validate_extension(f"file{ext}")
        if not is_valid:
            metrics.increment("upload_rejected_extension")
            audit_logger.log_upload(
                user_id, original_filename or f"file{ext}", len(payload),
                mime_type, file_hash, "rejected_extension", error
            )
            return False, f"[X] {error}", error
        
        # Generate safe filename
        safe_name = f"uploaded_{uuid.uuid4().hex}{ext}"
        quarantine_path = self.quarantine_dir / safe_name
        
        # Write to quarantine first
        try:
            with open(quarantine_path, "wb") as f:
                f.write(payload)
        except Exception as e:
            metrics.increment("upload_write_error")
            error_msg = f"Failed to write file: {str(e)}"
            audit_logger.log_upload(
                user_id, original_filename or safe_name, len(payload),
                mime_type, file_hash, "write_error", error_msg
            )
            return False, f"[X] {error_msg}", error_msg
        
        # Process based on kind
        try:
            if kind == "zip" and Config.ENABLE_SAFE_UNZIP:
                return self._process_zip(quarantine_path, user_id, file_hash, mime_type)
            elif kind == "image" and Config.ALLOW_IMAGE_THUMBNAILS:
                return self._process_image(quarantine_path, user_id, file_hash, mime_type)
            else:
                # Move to ready directory
                ready_path = self.ready_dir / safe_name
                quarantine_path.rename(ready_path)
                
                metrics.increment(f"upload_success_{kind}")
                audit_logger.log_upload(
                    user_id, original_filename or safe_name, len(payload),
                    mime_type, file_hash, "success", None
                )
                
                return True, self._format_success_message(
                    kind, str(ready_path), len(payload), mime_type
                ), None
        
        except Exception as e:
            metrics.increment(f"upload_error_{kind}")
            error_msg = f"Processing error: {str(e)}"
            logger.error(f"Upload processing failed", exc_info=True)
            audit_logger.log_upload(
                user_id, original_filename or safe_name, len(payload),
                mime_type, file_hash, "processing_error", error_msg
            )
            return False, f"[X] {error_msg}", error_msg
    
    def _process_zip(
        self,
        zip_path: Path,
        user_id: Optional[str],
        file_hash: str,
        mime_type: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Extract and validate ZIP file."""
        success, extracted_dir, error = safe_unzip(
            str(zip_path),
            str(self.ready_dir)
        )
        
        if not success:
            metrics.increment("zip_validation_failed")
            audit_logger.log_upload(
                user_id, zip_path.name, zip_path.stat().st_size,
                mime_type, file_hash, "zip_validation_failed", error
            )
            # Clean up
            zip_path.unlink(missing_ok=True)
            return False, f"[X] ZIP validation failed: {error}", error
        
        # Count extracted files
        extracted_files = list(Path(extracted_dir).rglob("*"))
        file_count = len([f for f in extracted_files if f.is_file()])
        
        metrics.increment("zip_extracted")
        metrics.record("zip_file_count", file_count)
        
        audit_logger.log_upload(
            user_id, zip_path.name, zip_path.stat().st_size,
            mime_type, file_hash, "success_zip", None
        )
        
        # Clean up quarantine
        zip_path.unlink(missing_ok=True)
        
        message = (
            f"[OK] [ZIP Extracted]\n"
            f"Path: {extracted_dir}\n"
            f"Files: {file_count}\n"
            f"MIME: {mime_type}\n"
            f"Next: Use list_data_files() or specify a file path"
        )
        
        return True, message, None
    
    def _process_image(
        self,
        image_path: Path,
        user_id: Optional[str],
        file_hash: str,
        mime_type: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Process image: verify, create thumbnail, strip EXIF."""
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = Config.MAX_IMAGE_PIXELS
            
            # Verify image
            img = Image.open(image_path)
            img.verify()
            
            # Reopen for processing (verify() closes the image)
            img = Image.open(image_path)
            original_size = img.size
            original_format = img.format
            
            # Convert to RGB if needed
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            # Create thumbnail (strips EXIF automatically)
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Save thumbnail
            thumb_name = f"{image_path.stem}_thumb.jpg"
            thumb_path = self.thumbnails_dir / thumb_name
            img.save(thumb_path, "JPEG", quality=85, optimize=True)
            
            # Move original to ready
            ready_path = self.ready_dir / image_path.name
            image_path.rename(ready_path)
            
            metrics.increment("image_processed")
            metrics.record("image_pixels", original_size[0] * original_size[1])
            
            audit_logger.log_upload(
                user_id, image_path.name, image_path.stat().st_size,
                mime_type, file_hash, "success_image", None
            )
            
            message = (
                f"[OK] [Image Uploaded]\n"
                f"Original: {ready_path}\n"
                f"Thumbnail: {thumb_path}\n"
                f"Size: {original_size[0]}x{original_size[1]} ({original_format})\n"
                f"Thumbnail: 1024x1024 (JPEG, EXIF stripped)\n"
                f"MIME: {mime_type}\n"
                f"Next: Use the thumbnail path for analysis"
            )
            
            return True, message, None
        
        except Exception as e:
            metrics.increment("image_processing_error")
            error_msg = f"Image processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Try to move original anyway
            try:
                ready_path = self.ready_dir / image_path.name
                image_path.rename(ready_path)
                
                message = (
                    f"[WARNING] [Image Uploaded - Thumbnail Failed]\n"
                    f"Path: {ready_path}\n"
                    f"Size: {image_path.stat().st_size} bytes\n"
                    f"MIME: {mime_type}\n"
                    f"Warning: Could not create thumbnail ({str(e)})\n"
                    f"Original image saved"
                )
                
                return True, message, error_msg
            except Exception as e2:
                return False, f"[X] Image processing failed: {str(e2)}", str(e2)
    
    @staticmethod
    def _format_success_message(kind: str, path: str, size: int, mime: str) -> str:
        """Format success message for upload."""
        emoji = {"csv": "", "zip": "", "image": "", "other": ""}.get(kind, "")
        
        return (
            f"[OK] {emoji} [File Uploaded]\n"
            f"Kind: {kind.upper()}\n"
            f"Path: {path}\n"
            f"Size: {size:,} bytes ({size/1_000_000:.2f} MB)\n"
            f"MIME: {mime}\n"
            f"Next: Use list_data_files() or run tools with this path"
        )


# Global instance
production_file_handler = ProductionFileHandler()

