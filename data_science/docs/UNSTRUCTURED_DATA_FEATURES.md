# Unstructured Data Processing - Implementation Summary

## ✅ What Was Added

### 1. New Tool Category: **Unstructured Data Processing** (7 tools)

#### 🔧 Tools Implemented:

1. **`extract_text(file_id, type_hint)`**
   - Extracts text from: PDF, DOCX, PPTX, HTML, images (OCR), audio (STT), emails (.eml/.mbox), JSON/XML
   - Outputs: JSONL with normalized text + metadata
   - Libraries: pymupdf, python-docx, trafilatura, pytesseract, whisper

2. **`chunk_text(file_id, max_tokens, overlap, by)`**
   - Token-aware chunking with configurable overlap
   - Strategies: sentence-based (NLTK) or fixed-size
   - Outputs: Parquet with chunks + metadata
   - Libraries: tiktoken, nltk

3. **`embed_and_index(file_id, model)`**
   - Generate embeddings using sentence-transformers
   - Create FAISS index for fast similarity search
   - Outputs: `.faiss` index + metadata sidecar
   - Libraries: sentence-transformers, faiss

4. **`semantic_search(query, file_id, k, filter_dict)`**
   - Meaning-based search (not keyword matching)
   - Returns top-k similar chunks with distances
   - Supports metadata filtering
   - Libraries: sentence-transformers, faiss

5. **`summarize_chunks(file_id, mode, max_chunks)`**
   - LLM-powered summarization (map-reduce or direct)
   - Map: summarize each chunk → Reduce: combine summaries
   - Outputs: comprehensive summary text
   - Libraries: litellm

6. **`classify_text(file_id, target, label_set, strategy)`**
   - **Supervised**: TF-IDF + Naive Bayes/SVM (fast, accurate for ham/spam)
   - **Zero-shot**: LLM classification (no labels needed)
   - Integrates with existing `text_to_features()` and sklearn tools
   - Libraries: sklearn, litellm

7. **`ingest_mailbox(file_id, split)`**
   - Parse `.eml` / `.mbox` files into structured CSV
   - Extracts: From, To, Subject, Date, Body
   - One row per message for easy labeling/analysis
   - Libraries: email (stdlib), mailbox (stdlib)

---

## 📂 File Structure

### New Files Created:

1. **`data_science/unstructured_config.py`**
   - Configuration for unstructured data processing
   - Environment variables: `ENABLE_UNSTRUCTURED`, `UNSTRUCTURED_MAX_CHUNK_TOKENS`, `EMBEDDING_MODEL`, `OCR_LANGS`
   - Directory setup: `.unstructured/`, `.vector/`, `.ocr_cache/`
   - MIME type definitions for all supported formats

2. **`data_science/unstructured_tools.py`**
   - All 7 unstructured data tools implemented
   - Auto-installation helpers for optional dependencies
   - ~700 lines of production-ready code

3. **`UNSTRUCTURED_DATA_FEATURES.md`** (this file)
   - Documentation and usage examples

### Modified Files:

1. **`data_science/agent.py`**
   - Imported 7 new tools
   - Registered with `SafeFunctionTool` wrapper
   - Updated instructions (84 tools total, up from 77)
   - Added "UNSTRUCTURED DATA PROMPTS" section with 8 example mappings

2. **`requirements.txt`**
   - Added unstructured dependencies:
     - `pymupdf` (PDF)
     - `python-docx` (DOCX)
     - `trafilatura` (HTML)
     - `pytesseract` (OCR)
     - `openai-whisper` (STT)
     - `tiktoken`, `nltk` (chunking)
   - Includes installation notes for Tesseract system dependency

---

## 🎯 Use Cases

### 1. **Ham/Spam Email Classification** (Supervised)

```python
# Step 1: Parse mailbox
ingest_mailbox("spam_corpus.mbox", split="per-message")
# Output: spam_corpus.mbox_parsed.csv with columns: from, to, subject, date, body

# Step 2: Classify (assumes 'label' column exists)
classify_text("spam_corpus.mbox", target="label", strategy="tfidf-sklearn")
# Uses TF-IDF + Naive Bayes (fast, accurate for text)
```

### 2. **Document Search & Q&A**

```python
# Step 1: Extract text from PDFs
extract_text("research_papers.pdf")
# Output: research_papers.pdf.jsonl

# Step 2: Chunk into windows
chunk_text("research_papers.pdf", max_tokens=800, overlap=120)
# Output: research_papers.pdf_chunks.parquet

# Step 3: Generate embeddings + index
embed_and_index("research_papers.pdf", model="all-MiniLM-L6-v2")
# Output: research_papers.pdf.faiss + metadata

# Step 4: Search by meaning
semantic_search(query="What are the side effects of aspirin?", k=10)
# Returns top 10 semantically similar chunks
```

### 3. **Document Summarization**

```python
# After extract + chunk + embed:
summarize_chunks("legal_contract.pdf", mode="map-reduce", max_chunks=50)
# LLM summarizes each chunk, then combines into final summary
```

### 4. **OCR from Scanned Documents**

```python
extract_text("scanned_invoice.png", type_hint="image/png")
# Uses pytesseract to extract text from image
```

### 5. **Audio Transcription**

```python
extract_text("meeting_recording.mp3", type_hint="audio/mp3")
# Uses OpenAI Whisper to transcribe speech to text
```

---

## 🔧 Configuration

### Environment Variables (`.env`):

```bash
# Enable unstructured data processing
ENABLE_UNSTRUCTURED=true

# Chunking settings
UNSTRUCTURED_MAX_CHUNK_TOKENS=800
UNSTRUCTURED_CHUNK_OVERLAP=120

# Embedding model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# OCR languages (for pytesseract)
OCR_LANGS=eng

# Storage directories (auto-created)
UNSTRUCTURED_ROOT=data_science/.unstructured
VECTOR_STORE_DIR=data_science/.vector
OCR_CACHE_DIR=data_science/.ocr_cache
```

---

## 📦 Dependencies

### Required (auto-install):
- `pymupdf` (PDF extraction)
- `python-docx` (DOCX extraction)
- `trafilatura` (HTML extraction)
- `pytesseract` (OCR - requires system Tesseract binary)
- `openai-whisper` (audio transcription)
- `tiktoken` (tokenization)
- `nltk` (sentence splitting)

### Already Installed:
- `sentence-transformers` (embeddings)
- `faiss-cpu` (vector search)
- `litellm` (LLM API)

### System Requirements:
- **Tesseract OCR** (for image text extraction):
  - **Auto-detection enabled!** The code checks these locations automatically:
    1. `C:\harfile\data_science\tesseract\tesseract.exe` (your custom location) ✅
    2. `C:\Program Files\Tesseract-OCR\tesseract.exe` (default Windows)
    3. `/usr/bin/tesseract` (Linux)
    4. `/usr/local/bin/tesseract` (Mac)
  - **Manual install** (if needed):
    - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
    - Mac: `brew install tesseract`
    - Linux: `apt-get install tesseract-ocr`

---

## 🚀 Workflow Examples

### **Ham/Spam Classifier (Labeled Data)**

```python
# 1. Ingest emails
ingest_mailbox("ham_spam_corpus.mbox")
# Output: ham_spam_corpus.mbox_parsed.csv

# 2. Classify
classify_text("ham_spam_corpus.mbox", target="label", strategy="tfidf-sklearn")
# Uses TF-IDF + Naive Bayes → fast, accurate

# 3. Evaluate
evaluate(target="label")

# 4. Export model card
export_model_card()
```

### **Ham/Spam Classifier (Unlabeled Data - Zero-shot)**

```python
# 1. Ingest emails
ingest_mailbox("unknown_emails.mbox")

# 2. Zero-shot classification via LLM
classify_text("unknown_emails.mbox", target="spam", label_set=["ham", "spam"], strategy="llm")
# LLM classifies each email (slower, but works without labels)

# 3. Review results, label a seed set, then retrain with supervised approach
```

### **PDF Document Search**

```python
# 1. Extract
extract_text("company_policies.pdf")

# 2. Chunk
chunk_text("company_policies.pdf", max_tokens=600, overlap=100)

# 3. Index
embed_and_index("company_policies.pdf")

# 4. Search
semantic_search(query="What is the remote work policy?", k=5)
# Returns top 5 relevant chunks
```

---

## 🎓 Agent Intelligence

The agent now understands these prompts:

| **User Says** | **Agent Runs** |
|--------------|---------------|
| "analyze this PDF" | `extract_text()` → `chunk_text()` → `embed_and_index()` |
| "parse these emails" | `ingest_mailbox()` → `classify_text(target='spam')` |
| "spam detection" | `ingest_mailbox()` → `classify_text(strategy='tfidf-sklearn')` |
| "search my documents for X" | `semantic_search(query='X')` |
| "summarize this paper" | `summarize_chunks(mode='map-reduce')` |
| "OCR this scan" | `extract_text(type_hint='image/png')` |
| "transcribe audio" | `extract_text(type_hint='audio/mp3')` |

---

## ✅ Testing Checklist

- [x] **Config**: `unstructured_config.py` with all env vars
- [x] **Tools**: All 7 functions implemented in `unstructured_tools.py`
- [x] **Registration**: Tools added to `agent.py` with `SafeFunctionTool`
- [x] **Instructions**: Agent prompt updated with unstructured data guidance
- [x] **Dependencies**: `requirements.txt` updated with all libraries
- [x] **No PHI Redaction**: Per requirements, no PII/PHI processing included
- [x] **No Linter Errors**: All files pass linting

---

## 🎉 Summary

- **7 new tools** for unstructured data processing
- **84 total tools** (up from 77)
- **Ham/spam classification** with TF-IDF + Naive Bayes (fast, accurate)
- **PDF/DOCX/HTML/image/audio** extraction
- **Semantic search** with FAISS
- **LLM-powered summarization**
- **Mailbox parsing** (.eml/.mbox)
- **Zero dependencies on Git/DVC** - fully self-contained
- **No PHI/PII redaction** per spec

Ready to handle text corpora, documents, emails, and more! 🚀

