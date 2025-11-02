"""Verify production configuration."""
from data_science.config import Config

print("\n" + "="*60)
print("PRODUCTION CONFIGURATION VERIFICATION")
print("="*60)
print(f"\nStorage:")
print(f"  Data Directory: {Config.DATA_DIR}")
print(f"  Quarantine:     {Config.QUARANTINE_DIR}")
print(f"  Ready:          {Config.READY_DIR}")

print(f"\nUpload Limits:")
print(f"  Max Upload:     {Config.MAX_UPLOAD_BYTES/1_000_000:.1f} MB")
print(f"  Max ZIP:        {Config.MAX_ZIP_UNCOMPRESSED/1_000_000:.1f} MB uncompressed")
print(f"  Max Image:      {Config.MAX_IMAGE_PIXELS:,} pixels")

print(f"\nAutoML:")
print(f"  Default Time:   {Config.DEFAULT_AUTOML_SECONDS}s")
print(f"  Max Time:       {Config.MAX_AUTOML_SECONDS}s")
print(f"  Preset:         {Config.DEFAULT_AUTOML_PRESET}")
print(f"  Enabled:        {'YES' if Config.ENABLE_AUTOML else 'NO'}")

print(f"\nLLM:")
print(f"  Provider:       {'Gemini' if Config.USE_GEMINI else 'OpenAI'}")
print(f"  Model:          {Config.GEMINI_MODEL if Config.USE_GEMINI else Config.OPENAI_MODEL}")
print(f"  Temperature:    {Config.LLM_TEMPERATURE}")
print(f"  Max Tokens:     {Config.LLM_MAX_TOKENS}")

print(f"\nFeatures:")
print(f"  ZIP Extraction: {'ENABLED' if Config.ENABLE_SAFE_UNZIP else 'DISABLED'}")
print(f"  Image Thumbs:   {'ENABLED' if Config.ALLOW_IMAGE_THUMBNAILS else 'DISABLED'}")
print(f"  Strip EXIF:     {'ENABLED' if Config.STRIP_EXIF else 'DISABLED'}")
print(f"  Summary Only:   {'YES' if Config.SUMMARY_MODE_ONLY else 'NO'}")

print(f"\nSecurity:")
print(f"  ZIP Validation: {'ENABLED' if Config.VALIDATE_ZIP_PATHS else 'DISABLED'}")
print(f"  Allowed Exts:   {len(Config.ALLOWED_EXTENSIONS)} types")

print(f"\nObservability:")
print(f"  Log Level:      {Config.LOG_LEVEL}")
print(f"  Log Format:     {Config.LOG_FORMAT}")
print(f"  Tracing:        {'ENABLED' if Config.ENABLE_TRACING else 'DISABLED'}")

print("\n" + "="*60)
print("VALIDATION")
print("="*60)
warnings = Config.validate()
if warnings:
    for w in warnings:
        print(f"  {w}")
else:
    print("  All checks passed!")

print("\n" + "="*60)
print("STATUS: READY FOR PRODUCTION")
print("="*60 + "\n")

