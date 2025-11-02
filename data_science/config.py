"""
Production-grade configuration for Data Science Agent.

Environment variables control all limits, paths, and feature flags.
Validates at import time to fail fast on misconfiguration.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional


class Config:
    """Centralized configuration with validation and safe defaults."""
    
    # ==================== STORAGE ====================
    DATA_DIR: str = os.getenv("DATA_DIR") or os.path.join(tempfile.gettempdir(), "data_science_agent")
    QUARANTINE_DIR: str = os.path.join(DATA_DIR, "quarantine")
    READY_DIR: str = os.path.join(DATA_DIR, "ready")
    THUMBNAILS_DIR: str = os.path.join(DATA_DIR, "thumbnails")
    
    # ==================== UPLOAD LIMITS ====================
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", "50_000_000"))  # 50 MB
    MAX_ZIP_ENTRIES: int = int(os.getenv("MAX_ZIP_ENTRIES", "200"))
    MAX_ZIP_UNCOMPRESSED: int = int(os.getenv("MAX_ZIP_UNCOMPRESSED", "500_000_000"))  # 500 MB
    MAX_IMAGE_PIXELS: int = int(os.getenv("MAX_IMAGE_PIXELS", "50_000_000"))  # ~7000x7000
    MAX_LLM_ATTACHMENT: int = int(os.getenv("MAX_LLM_ATTACHMENT", "2_000_000"))  # 2 MB
    
    # ==================== DATA PROCESSING LIMITS ====================
    MAX_CSV_ROWS: int = int(os.getenv("MAX_CSV_ROWS", "1_000_000"))
    MAX_CSV_COLS: int = int(os.getenv("MAX_CSV_COLS", "1000"))
    MAX_ROWS_COLS_PRODUCT: int = int(os.getenv("MAX_ROWS_COLS_PRODUCT", "5_000_000"))
    AUTO_SAMPLE_THRESHOLD: int = int(os.getenv("AUTO_SAMPLE_THRESHOLD", "100_000"))  # Sample if > 100k rows
    
    # ==================== AUTOML LIMITS ====================
    MAX_AUTOML_SECONDS: int = int(os.getenv("MAX_AUTOML_SECONDS", "600"))  # 10 minutes
    DEFAULT_AUTOML_SECONDS: int = int(os.getenv("DEFAULT_AUTOML_SECONDS", "60"))
    DEFAULT_AUTOML_PRESET: str = os.getenv("DEFAULT_AUTOML_PRESET", "medium_quality")
    
    # ==================== LLM SETTINGS ====================
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GENAI_MODEL", "gemini-2.0-flash-exp")
    USE_GEMINI: bool = os.getenv("USE_GEMINI", "false").lower() in ("true", "1", "yes")
    
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))  # Deterministic
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "40"))
    
    # ==================== FEATURE FLAGS ====================
    SUMMARY_MODE_ONLY: bool = os.getenv("SUMMARY_MODE_ONLY", "false").lower() in ("true", "1", "yes")
    ALLOW_IMAGE_THUMBNAILS: bool = os.getenv("ALLOW_IMAGE_THUMBNAILS", "true").lower() in ("true", "1", "yes")
    ENABLE_SAFE_UNZIP: bool = os.getenv("ENABLE_SAFE_UNZIP", "true").lower() in ("true", "1", "yes")
    AUTO_ROUTE_GEMINI: bool = os.getenv("AUTO_ROUTE_GEMINI", "false").lower() in ("true", "1", "yes")
    ENABLE_AUTOML: bool = os.getenv("ENABLE_AUTOML", "true").lower() in ("true", "1", "yes")
    
    # ==================== SECURITY ====================
    ALLOWED_EXTENSIONS: tuple = (".csv", ".tsv", ".json", ".parquet", ".txt", ".jpg", ".jpeg", ".png", ".gif", ".zip")
    STRIP_EXIF: bool = os.getenv("STRIP_EXIF", "true").lower() in ("true", "1", "yes")
    VALIDATE_ZIP_PATHS: bool = os.getenv("VALIDATE_ZIP_PATHS", "true").lower() in ("true", "1", "yes")
    
    # ==================== RELIABILITY ====================
    UPLOAD_TIMEOUT_SECONDS: int = int(os.getenv("UPLOAD_TIMEOUT_SECONDS", "30"))
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_BASE_DELAY: float = float(os.getenv("RETRY_BASE_DELAY", "0.5"))
    RETRY_MAX_DELAY: float = float(os.getenv("RETRY_MAX_DELAY", "8.0"))
    
    # ==================== OBSERVABILITY ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # "json" or "text"
    ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "false").lower() in ("true", "1", "yes")
    
    # ==================== COST CONTROLS ====================
    MAX_TOKENS_PER_REQUEST: int = int(os.getenv("MAX_TOKENS_PER_REQUEST", "10_000"))
    ENABLE_COST_ALERTS: bool = os.getenv("ENABLE_COST_ALERTS", "false").lower() in ("true", "1", "yes")
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of warnings/errors."""
        warnings = []
        
        # Check critical settings
        if not cls.OPENAI_API_KEY and not cls.USE_GEMINI:
            warnings.append("[WARNING]  OPENAI_API_KEY not set and USE_GEMINI=false - LLM will fail")
        
        # Check reasonable limits
        if cls.MAX_UPLOAD_BYTES > 100_000_000:  # 100 MB
            warnings.append(f"[WARNING]  MAX_UPLOAD_BYTES is very large: {cls.MAX_UPLOAD_BYTES:,}")
        
        if cls.MAX_AUTOML_SECONDS > 3600:  # 1 hour
            warnings.append(f"[WARNING]  MAX_AUTOML_SECONDS is very large: {cls.MAX_AUTOML_SECONDS}")
        
        if cls.LLM_TEMPERATURE < 0 or cls.LLM_TEMPERATURE > 2:
            warnings.append(f"[WARNING]  LLM_TEMPERATURE out of range: {cls.LLM_TEMPERATURE}")
        
        return warnings
    
    @classmethod
    def initialize_directories(cls) -> None:
        """Create required directories with secure permissions."""
        for dir_path in [cls.DATA_DIR, cls.QUARANTINE_DIR, cls.READY_DIR, cls.THUMBNAILS_DIR]:
            Path(dir_path).mkdir(mode=0o700, parents=True, exist_ok=True)
    
    @classmethod
    def summary(cls) -> str:
        """Return human-readable config summary."""
        return f"""
╔══════════════════════════════════════════════════════════════╗
║        DATA SCIENCE AGENT - PRODUCTION CONFIGURATION         ║
╚══════════════════════════════════════════════════════════════╝

 STORAGE:
   Data Directory:        {cls.DATA_DIR}
   Quarantine:           {cls.QUARANTINE_DIR}
   Ready:                {cls.READY_DIR}

 UPLOAD LIMITS:
   Max Upload Size:      {cls.MAX_UPLOAD_BYTES:,} bytes ({cls.MAX_UPLOAD_BYTES/1_000_000:.1f} MB)
   Max ZIP Entries:      {cls.MAX_ZIP_ENTRIES}
   Max ZIP Uncompressed: {cls.MAX_ZIP_UNCOMPRESSED:,} bytes ({cls.MAX_ZIP_UNCOMPRESSED/1_000_000:.1f} MB)
   Max Image Pixels:     {cls.MAX_IMAGE_PIXELS:,}

 AUTOML:
   Default Time Limit:   {cls.DEFAULT_AUTOML_SECONDS}s
   Max Time Limit:       {cls.MAX_AUTOML_SECONDS}s
   Default Preset:       {cls.DEFAULT_AUTOML_PRESET}
   Enabled:              {'[OK]' if cls.ENABLE_AUTOML else '[X]'}

 LLM:
   Model:                {'Gemini' if cls.USE_GEMINI else f'OpenAI {cls.OPENAI_MODEL}'}
   Temperature:          {cls.LLM_TEMPERATURE}
   Max Tokens:           {cls.LLM_MAX_TOKENS}
   Timeout:              {cls.LLM_TIMEOUT_SECONDS}s

  SECURITY:
   Allowed Extensions:   {', '.join(cls.ALLOWED_EXTENSIONS)}
   Strip EXIF:           {'[OK]' if cls.STRIP_EXIF else '[X]'}
   Validate ZIP Paths:   {'[OK]' if cls.VALIDATE_ZIP_PATHS else '[X]'}

 FEATURES:
   Summary Mode Only:    {'[OK]' if cls.SUMMARY_MODE_ONLY else '[X]'}
   Image Thumbnails:     {'[OK]' if cls.ALLOW_IMAGE_THUMBNAILS else '[X]'}
   Safe Unzip:           {'[OK]' if cls.ENABLE_SAFE_UNZIP else '[X]'}

 OBSERVABILITY:
   Log Level:            {cls.LOG_LEVEL}
   Log Format:           {cls.LOG_FORMAT}
   Tracing:              {'[OK]' if cls.ENABLE_TRACING else '[X]'}

╚══════════════════════════════════════════════════════════════╝
"""


# Auto-validate on import
_warnings = Config.validate()
if _warnings:
    import sys
    print("\n[WARNING]  Configuration Warnings:", file=sys.stderr)
    for w in _warnings:
        print(f"  {w}", file=sys.stderr)
    print()

# Auto-initialize directories
Config.initialize_directories()

