"""
Configuration for unstructured data processing.
No PHI/PII redaction included per requirements.
"""
import os
from pathlib import Path

# Root directories
WORKSPACE_ROOT = Path(__file__).parent
UNSTRUCTURED_ROOT = Path(os.getenv("UNSTRUCTURED_ROOT", WORKSPACE_ROOT / ".unstructured"))
VECTOR_STORE_DIR = Path(os.getenv("VECTOR_STORE_DIR", WORKSPACE_ROOT / ".vector"))
OCR_CACHE_DIR = Path(os.getenv("OCR_CACHE_DIR", WORKSPACE_ROOT / ".ocr_cache"))

# Ensure directories exist
UNSTRUCTURED_ROOT.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Feature flags
ENABLE_UNSTRUCTURED = os.getenv("ENABLE_UNSTRUCTURED", "true").lower() == "true"

# Chunking params
UNSTRUCTURED_MAX_CHUNK_TOKENS = int(os.getenv("UNSTRUCTURED_MAX_CHUNK_TOKENS", "800"))
UNSTRUCTURED_CHUNK_OVERLAP = int(os.getenv("UNSTRUCTURED_CHUNK_OVERLAP", "120"))

# Embedding config
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# OCR config
OCR_LANGS = os.getenv("OCR_LANGS", "eng")

# Supported MIME types
SUPPORTED_TEXT_MIMES = {
    "text/plain",
    "text/markdown",
    "text/html",
    "message/rfc822",  # .eml
    "application/mbox",
}

SUPPORTED_DOC_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
}

SUPPORTED_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
}

SUPPORTED_AUDIO_MIMES = {
    "audio/wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/m4a",
    "audio/x-m4a",
}

SUPPORTED_SEMI_STRUCTURED_MIMES = {
    "application/json",
    "application/x-ndjson",  # JSONL
    "application/xml",
    "text/xml",
}

ALL_UNSTRUCTURED_MIMES = (
    SUPPORTED_TEXT_MIMES
    | SUPPORTED_DOC_MIMES
    | SUPPORTED_IMAGE_MIMES
    | SUPPORTED_AUDIO_MIMES
    | SUPPORTED_SEMI_STRUCTURED_MIMES
)

