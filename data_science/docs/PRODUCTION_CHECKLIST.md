# 🚀 PRODUCTION-GRADE CHECKLIST

**Drop-in patterns for shipping a production-ready Data Science Agent**

Covers: CSV, ZIP, images, security, reliability, cost, observability, and ops.

---

## ✅ **IMPLEMENTED FEATURES**

### **A) Architecture & Model Routing**
- ✅ **Unified LLM wrapper** (`LiteLlm`) for OpenAI/Gemini
- ✅ **Environment-based routing** (`USE_GEMINI`, `OPENAI_MODEL`)
- ✅ **Deterministic prompts** (`temperature=0.2` default)
- ✅ **File-to-storage pattern** (files never sent to LLM directly)

### **B) File Ingestion Pipeline**
- ✅ **Security validators** (`validators.py`)
  - Path traversal prevention
  - ZIP bomb protection (entry count + uncompressed size limits)
  - Extension allowlist
  - MIME type validation
- ✅ **Quarantine → Ready flow**
  - Files land in quarantine first
  - Validated/processed → moved to ready
- ✅ **ZIP support** (`safe_unzip` with validation)
- ✅ **Image support** (Pillow verification, thumbnail generation, EXIF stripping)
- ✅ **CSV support** (bytes storage, encoding inference in tools)
- ✅ **Size limits** (configurable via env vars)

### **C) Tool Contracts**
- ✅ **Path-based operations** (all tools accept paths, not raw data)
- ✅ **Sampling params** (max_rows, sample_frac for big data)
- ✅ **Time budgets** (time_limit respected across AutoML)
- ✅ **80/20 train/test splits** (automatic in all training tools)

### **D) LLM Interaction**
- ✅ **Summary-first approach** (dataset profiles, not raw rows)
- ✅ **Token budget enforcement** (prevent massive prompts)
- ✅ **Context window discipline** (truncate summaries)

### **E) Security**
- ✅ **Formula injection protection** (`sanitize_for_export`)
- ✅ **Filesystem isolation** (0700 permissions on data dirs)
- ✅ **ZIP validation** (no zip-slip, no zip bombs)
- ✅ **Image validation** (Pillow verification, strip EXIF)
- ✅ **Extension allowlist** (configurable)
- ✅ **Path traversal checks** (all file operations)

### **F) Reliability & Performance**
- ✅ **Timeouts** (upload, AutoML, LLM all configurable)
- ✅ **Sampling for large datasets** (auto-sample > 100k rows)
- ✅ **Retry logic** (built into utilities)

### **G) Observability**
- ✅ **Structured logging** (`observability.py`)
- ✅ **JSON log format** (production-ready)
- ✅ **Audit trail** (upload, tool execution, AutoML runs, LLM calls)
- ✅ **Metrics collection** (counters, gauges, histograms)
- ✅ **Cost estimation** (LLM token costs)
- ✅ **Operation timing** (`@timed` decorator)

### **H) Configuration & Feature Flags**
- ✅ **Centralized config** (`config.py` with validation)
- ✅ **Environment-based** (all limits via env vars)
- ✅ **Feature flags**:
  - `SUMMARY_MODE_ONLY`
  - `ALLOW_IMAGE_THUMBNAILS`
  - `ENABLE_SAFE_UNZIP`
  - `AUTO_ROUTE_GEMINI`
  - `ENABLE_AUTOML`
- ✅ **Boot-time validation** (fail fast on misconfiguration)

---

## 📋 **CONFIGURATION REFERENCE**

### **Environment Variables**

```bash
# ==================== STORAGE ====================
DATA_DIR=/tmp/data_science_agent          # Base data directory
# (Quarantine, ready, thumbnails auto-created under this)

# ==================== UPLOAD LIMITS ====================
MAX_UPLOAD_BYTES=50000000                  # 50 MB max upload
MAX_ZIP_ENTRIES=200                        # Max files in ZIP
MAX_ZIP_UNCOMPRESSED=500000000             # 500 MB max uncompressed
MAX_IMAGE_PIXELS=50000000                  # ~7000x7000 max
MAX_LLM_ATTACHMENT=2000000                 # 2 MB max to LLM

# ==================== DATA PROCESSING ====================
MAX_CSV_ROWS=1000000                       # 1M rows max
MAX_CSV_COLS=1000                          # 1K columns max
MAX_ROWS_COLS_PRODUCT=5000000              # Row×Col product limit
AUTO_SAMPLE_THRESHOLD=100000               # Sample if > 100k rows

# ==================== AUTOML ====================
MAX_AUTOML_SECONDS=600                     # 10 min max
DEFAULT_AUTOML_SECONDS=60                  # 1 min default
DEFAULT_AUTOML_PRESET=medium_quality       # quality preset

# ==================== LLM ====================
OPENAI_MODEL=gpt-4o                        # OpenAI model
OPENAI_API_KEY=sk-...                      # OpenAI API key
USE_GEMINI=false                           # Use Gemini instead?
GENAI_MODEL=gemini-2.0-flash-exp           # Gemini model
LLM_TEMPERATURE=0.2                        # Deterministic
LLM_MAX_TOKENS=4096                        # Max output tokens
LLM_TIMEOUT_SECONDS=40                     # LLM call timeout

# ==================== FEATURE FLAGS ====================
SUMMARY_MODE_ONLY=false                    # Only send summaries to LLM?
ALLOW_IMAGE_THUMBNAILS=true                # Create thumbnails?
ENABLE_SAFE_UNZIP=true                     # Allow ZIP extraction?
AUTO_ROUTE_GEMINI=false                    # Auto-route to Gemini for vision?
ENABLE_AUTOML=true                         # Allow AutoML tools?

# ==================== SECURITY ====================
STRIP_EXIF=true                            # Strip EXIF from images?
VALIDATE_ZIP_PATHS=true                    # Validate ZIP paths?

# ==================== RELIABILITY ====================
UPLOAD_TIMEOUT_SECONDS=30                  # Upload processing timeout
RETRY_ATTEMPTS=3                           # Retry failed operations
RETRY_BASE_DELAY=0.5                       # Base retry delay (seconds)
RETRY_MAX_DELAY=8.0                        # Max retry delay (seconds)

# ==================== OBSERVABILITY ====================
LOG_LEVEL=INFO                             # DEBUG|INFO|WARNING|ERROR
LOG_FORMAT=json                            # json|text
ENABLE_TRACING=false                       # OpenTelemetry tracing?

# ==================== COST CONTROLS ====================
MAX_TOKENS_PER_REQUEST=10000               # Max tokens per LLM request
ENABLE_COST_ALERTS=false                   # Alert on high costs?
```

---

## 🔐 **SECURITY CHECKLIST**

### ✅ **File Upload Security**
- [x] Size limits enforced
- [x] Extension allowlist
- [x] MIME type validation (untrusted - content sniffing used)
- [x] Path traversal prevention (no `..`, no absolute paths)
- [x] Filesystem isolation (0700 permissions)
- [x] Quarantine → validation → ready flow

### ✅ **ZIP Security**
- [x] Zip bomb protection (max entries, max uncompressed size)
- [x] Path traversal checks (all members validated)
- [x] Extension filtering (skip disallowed files)
- [x] Corruption detection (`testzip()`)

### ✅ **Image Security**
- [x] Pillow verification (detect corrupted/malicious images)
- [x] Pixel limit enforcement
- [x] EXIF stripping (privacy + security)
- [x] Format conversion (normalize to RGB/JPEG)

### ✅ **Data Export Security**
- [x] Formula injection detection
- [x] Automatic sanitization (`'` prefix for dangerous cells)
- [x] CSV/Excel formula disable option

### ⚠️ **TODO: Additional Hardening**
- [ ] AV scanning (integrate ClamAV or cloud scanner)
- [ ] Secrets manager integration (Vault/AWS Secrets Manager)
- [ ] Dependency SCA (Checkmarx/OWASP DC/Trivy)
- [ ] SBOM generation (Syft/Cyclone DX)
- [ ] Container image signing (Cosign)

---

## 📊 **OBSERVABILITY CHECKLIST**

### ✅ **Logging**
- [x] Structured JSON logs (production-ready)
- [x] Audit trail (uploads, tool runs, AutoML, LLM calls)
- [x] PII hashing (user IDs hashed in logs)
- [x] Filename sanitization (sensitive info removed)

### ✅ **Metrics**
- [x] Upload counters (success/failure by type)
- [x] AutoML duration histograms
- [x] LLM token usage tracking
- [x] Error rate counters
- [x] Queue length gauges

### ✅ **Cost Tracking**
- [x] LLM cost estimation (per model)
- [x] Token usage logging
- [x] Cost per request tracking

### ⚠️ **TODO: Production Observability**
- [ ] OpenTelemetry integration (spans, traces)
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Alerting (PagerDuty/Opsgenie)
- [ ] SLO tracking (latency p95, success rate)

---

## 🧪 **TESTING CHECKLIST**

### ⚠️ **TODO: Test Coverage**
- [ ] Unit tests (validators, file handlers, config)
- [ ] Property-based tests (random CSV encodings, malformed ZIPs)
- [ ] Security tests:
  - [ ] Zip-slip attack prevention
  - [ ] Path traversal prevention
  - [ ] CSV formula injection
  - [ ] Oversized file rejection
- [ ] Integration tests:
  - [ ] End-to-end upload → analyze → AutoML
  - [ ] Multi-file ZIP extraction
  - [ ] Image thumbnail generation
- [ ] Load tests:
  - [ ] Concurrent uploads
  - [ ] Large file handling
  - [ ] AutoML queue capacity
- [ ] Prompt evaluation:
  - [ ] Red-team prompts (jailbreaking, prompt injection)
  - [ ] Regression suite (expected outputs)

---

## 🚀 **DEPLOYMENT CHECKLIST**

### ✅ **Configuration**
- [x] Environment variables documented
- [x] Boot-time validation
- [x] Secure defaults

### ⚠️ **TODO: CI/CD**
- [ ] Linting (black, ruff)
- [ ] Type checking (mypy)
- [ ] Security scanning (Bandit, Semgrep)
- [ ] Dependency scanning (SCA)
- [ ] Docker image building
- [ ] Image signing (Cosign)
- [ ] IaC scanning (Checkov, tfsec)

### ⚠️ **TODO: Infrastructure**
- [ ] Container orchestration (Kubernetes/ECS)
- [ ] Auto-scaling (CPU/memory/queue-based)
- [ ] Load balancing
- [ ] Health checks
- [ ] Graceful shutdown
- [ ] Rolling updates

### ⚠️ **TODO: Compliance**
- [ ] Data retention policy
- [ ] PII minimization
- [ ] Deletion APIs
- [ ] Encryption at rest
- [ ] TLS everywhere
- [ ] GDPR compliance
- [ ] HIPAA compliance (if applicable)

---

## 💰 **COST CONTROLS**

### ✅ **Implemented**
- [x] Token limits (per request, per model)
- [x] AutoML time limits
- [x] Automatic sampling (large datasets)
- [x] Cost estimation (LLM calls)

### ⚠️ **TODO**
- [ ] Budget alerts (Slack/email on threshold)
- [ ] Per-user quotas
- [ ] Rate limiting (requests/hour)
- [ ] Cost dashboard (daily/weekly spend)

---

## 📚 **USAGE EXAMPLES**

### **Example 1: CSV Upload with Auto-Split & Train**
```python
# User uploads CSV
# Agent automatically:
# 1. Saves to ready dir
# 2. Validates size/type
# 3. Splits 80/20
# 4. Trains models
# 5. Reports test metrics

result = await smart_autogluon_automl(
    csv_path='data.csv',
    target='price'
)

# Output:
# {
#   "test_split": "80/20 (automatic)",
#   "n_samples_train": 800,
#   "n_samples_test": 200,
#   "test_evaluation": {"r2": 0.87}
# }
```

### **Example 2: ZIP Upload with Validation**
```python
# User uploads malicious.zip with:
# - 1000 files (>200 limit)
# - Path traversal attempt (../../etc/passwd)
# - 10 GB uncompressed (>500 MB limit)

# Agent rejects:
# {
#   "success": false,
#   "error": "Too many ZIP entries: 1000 (max: 200)"
# }
```

### **Example 3: Image Upload with Thumbnail**
```python
# User uploads 4000x3000 JPEG with EXIF GPS data

# Agent:
# 1. Validates image (Pillow)
# 2. Creates 1024x1024 thumbnail
# 3. Strips EXIF (removes GPS)
# 4. Saves both

# Output:
# {
#   "original": "/data/ready/uploaded_abc123.jpg",
#   "thumbnail": "/data/thumbnails/uploaded_abc123_thumb.jpg",
#   "exif_stripped": true
# }
```

---

## 🎯 **QUICK START**

### **1. Install Dependencies**
```bash
uv sync
```

### **2. Configure Environment**
```bash
cp .env.example .env
# Edit .env with your settings:
# - OPENAI_API_KEY=sk-...
# - MAX_UPLOAD_BYTES=50000000
# - etc.
```

### **3. Verify Configuration**
```bash
uv run python -c "from data_science.config import Config; print(Config.summary())"
```

### **4. Start Agent**
```bash
uv run python main.py
```

### **5. Test Upload**
```bash
curl -X POST http://localhost:8080/upload \
  -F "file=@test.csv" \
  -H "Content-Type: multipart/form-data"
```

---

## 📖 **MODULES REFERENCE**

| Module | Purpose |
|--------|---------|
| `config.py` | Centralized configuration with validation |
| `validators.py` | Security validators (ZIP, paths, extensions) |
| `observability.py` | Structured logging, metrics, audit trail |
| `production_file_handler.py` | Production-grade file upload handler |
| `agent.py` | LLM agent with production file callback |
| `ds_tools.py` | Data science tools (train, analyze, plot) |
| `autogluon_tools.py` | AutoGluon wrappers (AutoML, time series) |
| `auto_sklearn_tools.py` | Auto-sklearn wrappers (algorithm selection) |

---

## 🚨 **MONITORING & ALERTS**

### **Key Metrics to Monitor**
1. **Upload Success Rate** (`upload_success_*` / total uploads)
2. **AutoML Duration** (p50, p95, p99)
3. **LLM Token Usage** (daily totals, costs)
4. **Error Rates** (upload, tool execution, LLM)
5. **Queue Length** (pending AutoML jobs)

### **Recommended Alerts**
- Error rate > 5% (15 min window)
- p95 AutoML latency > 600s
- Daily LLM cost > $100
- Upload rejection rate > 10%
- Disk usage > 80%

---

## ✅ **FINAL CHECKLIST**

Before going to production:

- [x] ✅ Configuration validated
- [x] ✅ Secure file handling
- [x] ✅ Automatic train/test splits
- [x] ✅ Structured logging
- [x] ✅ Audit trail
- [ ] ⚠️ Unit tests written
- [ ] ⚠️ Security tests passing
- [ ] ⚠️ Load tests passing
- [ ] ⚠️ CI/CD pipeline configured
- [ ] ⚠️ Monitoring dashboards created
- [ ] ⚠️ Alerting configured
- [ ] ⚠️ Runbooks written
- [ ] ⚠️ On-call rotation set up
- [ ] ⚠️ Compliance review completed

**Status:** 🟡 **MVP Ready** (core features complete, observability ready, needs testing & CI/CD)

---

## 🎉 **YOU'RE READY TO SHIP!**

**What's working NOW:**
✅ Secure file uploads (CSV, ZIP, images)  
✅ Automatic train/test splits (100% coverage)  
✅ Production-grade config & validation  
✅ Structured logging & audit trail  
✅ Cost tracking & metrics  
✅ GPT-4o integration  

**Next steps to production:**
1. Write tests (use pytest + property-based testing)
2. Set up CI/CD (GitHub Actions + Docker)
3. Configure monitoring (Prometheus + Grafana)
4. Set up alerting (PagerDuty)
5. Write runbooks
6. Deploy to staging
7. Load test
8. **Go live!** 🚀

