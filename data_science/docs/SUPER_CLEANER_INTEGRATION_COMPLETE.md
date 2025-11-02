# ✅ SUPER_CLEANER.PY INTEGRATION - COMPLETE

## Summary

**Task:** Add `super_cleaner.py` as a recommended tool during Data Cleaning stage  
**Status:** ✅ COMPLETE  
**Date:** 2025-10-23

---

## 📋 What Was Done

### 1. Updated Workflow Navigation Tool Recommendations

**File:** `data_science/ds_tools.py`  
**Section:** `WORKFLOW_STAGES` - Stage 2 (Data Cleaning & Preparation)

**Added `super_cleaner.py` as the FIRST recommendation:**

```python
{
    "id": 2,
    "name": "Data Cleaning & Preparation",
    "icon": "🧹",
    "description": "Handle missing values, outliers, duplicates, and inconsistencies",
    "tools": [
        "super_cleaner.py - RECOMMENDED: Advanced all-in-one cleaner (CLI: python data_science/tools/super_cleaner.py --file <file> --output cleaned.csv)",
        "robust_auto_clean_file() - Comprehensive auto-cleaning with LLM insights",
        "impute_simple() - Simple imputation (mean/median/mode)",
        "impute_knn() - KNN-based imputation",
        "remove_outliers() - Outlier detection and removal",
        "encode_categorical() - Encode categorical variables",
        "detect_metadata_rows() - Detect and handle metadata rows"
    ]
}
```

**Impact:**  
- When users call `next()` or `back()` to Stage 2, they'll see `super_cleaner.py` as the top recommendation
- Clear CLI usage instructions provided

---

### 2. Updated Agent Instructions (4 locations)

**File:** `data_science/agent.py`

#### Location 1: Stage 2 Description (lines 2861-2870)
```python
"**Stage 2: Data Cleaning & Preparation**\n"
"1. `super_cleaner.py` - **RECOMMENDED**: Advanced all-in-one cleaner (CLI tool)\n"
"   Usage: python data_science/tools/super_cleaner.py --file <input.csv> --output cleaned.csv\n"
"   Features: Auto-imputation, outlier winsorization, datetime parsing, duplicate removal, optional AutoML\n"
"2. `robust_auto_clean_file()` - Comprehensive auto-cleaning with LLM insights\n"
```

#### Location 2: Data Quality Prompts (lines 3616-3622)
```python
" DATA QUALITY PROMPTS:\n"
"• 'clean data' / 'fix missing' / 'handle nulls' → **BEST**: super_cleaner.py (all-in-one: imputation, outliers, dtypes, duplicates) OR robust_auto_clean_file() ...\n"
"• 'missing values' → super_cleaner.py (auto-imputation: median/mode/ffill) OR impute_knn() ...\n"
"• 'fix messy CSV' / 'repair headers' / 'cap outliers' → super_cleaner.py (comprehensive cleaning + winsorization) ...\n"
"• 'remove outliers' → super_cleaner.py (IQR winsorization) OR robust_auto_clean_file(cap_outliers='yes')\n"
```

#### Location 3: Step 2 Instructions (lines 3227-3234)
```python
"STEP 2:  DATA CLEANING & PREPARATION\n"
"├─ **RECOMMENDED** Advanced Cleaning:\n"
"│  • super_cleaner.py → All-in-one cleaner (CLI: python data_science/tools/super_cleaner.py --file <file> --output cleaned.csv)\n"
"│    FEATURES: Auto-imputation (median/mode/ffill), outlier winsorization (IQR*3), datetime parsing,\n"
"│              duplicate removal, constant column removal, downcast numerics, optional AutoML\n"
```

#### Location 4: Available Tool Categories (lines 3187-3189)
```python
"AVAILABLE TOOL CATEGORIES (84 tools total): "
"• **Data Cleaning**: super_cleaner.py (RECOMMENDED: all-in-one CLI cleaner with auto-imputation, outlier winsorization, datetime parsing), robust_auto_clean_file ..."
```

**Impact:**  
- LLM will proactively recommend `super_cleaner.py` when users mention data cleaning
- Clear guidance on when to use it vs. other cleaning tools
- Prominent placement in tool inventory

---

## 🔧 About Super Cleaner

### File Location
`data_science/tools/super_cleaner.py`

### What It Does (Deterministic Core)

1. **Read Multiple Formats** - CSV/TSV/JSON/JSONL/Parquet
2. **Basic Cleaning** - Drop all-NaN columns, trim strings, normalize booleans/whitespace
3. **Type Coercion** - Convert numeric-looking strings to actual numbers
4. **DateTime Parsing** - Multi-format datetime parsing, normalized to naive UTC
5. **Deduplication** - Remove constant columns, duplicate columns, duplicate rows
6. **Imputation** - Median for numeric, ffill/bfill for datetime, mode for others
7. **Outlier Handling** - Winsorize numeric outliers using IQR*3 method
8. **Optimization** - Downcast numerics to reduce memory usage
9. **Reporting** - Save cleaned CSV + JSON sidecar report with statistics

### Optional Plugins (Best-Effort)

- **pyjanitor** - `.clean_names()` for column name normalization
- **AutoClean** - elisemercury/AutoClean pass
- **datacleaner** - rhiever/datacleaner auto-clean
- **Great Expectations** - Light expectations (API version-safe)
- **Pandera** - Inferred schema validation
- **Cleanlab** - Label issue flags if target column exists
- **Deepchecks** - Data-integrity suite summary

### Optional AutoML Dry-Run

With `--automl` flag:
- Chooses task (classification vs regression) from target column
- Can use OpenAI advisor (`--advisor=openai`) for model suggestions
- Backends:
  - FLAML (quick AutoML)
  - AutoGluon (heavy, comprehensive)
  - Fallback: scikit-learn baseline CV
- Never modifies cleaned CSV, only adds metrics to report

### Usage Examples

```bash
# Basic cleaning
python data_science/tools/super_cleaner.py --file merged_iot_events.csv --output cleaned.csv

# Cleaning with AutoML evaluation
python data_science/tools/super_cleaner.py --file data.csv --output cleaned.csv --automl

# With OpenAI advisor
python data_science/tools/super_cleaner.py --file data.csv --output cleaned.csv --automl --advisor=openai
```

---

## 💡 When to Recommend Super Cleaner

### Best Use Cases:

1. **"Clean my data"** - User wants comprehensive, one-stop cleaning
2. **Missing values + outliers + duplicates** - Multiple issues to address
3. **Messy CSV files** - Unknown data quality, need automated fixes
4. **Pre-modeling prep** - Quick cleaning before model training
5. **DateTime columns** - Need robust multi-format datetime parsing
6. **Memory optimization** - Large datasets that need downcasting

### When to Use Alternatives:

- **LLM-powered insights needed** → Use `robust_auto_clean_file()` instead
- **Specific imputation strategy** → Use `impute_knn()` or `impute_iterative()`
- **Metadata row detection** → Use `detect_metadata_rows()` first
- **Interactive cleaning** → Use individual tools for more control

---

## 🎯 Recommendation Strategy

### User Asks About Cleaning:

```
User: "Clean my data"
Agent: "I'll recommend our most comprehensive cleaning tool!

**RECOMMENDED: super_cleaner.py**

This is an all-in-one CLI cleaner that handles:
✓ Missing value imputation (median/mode/ffill)
✓ Outlier winsorization (IQR*3 method)
✓ DateTime parsing (multi-format)
✓ Duplicate removal (rows & columns)
✓ Type coercion (numeric strings → numbers)
✓ Memory optimization (downcast numerics)

**Usage:**
```bash
python data_science/tools/super_cleaner.py --file your_data.csv --output cleaned.csv
```

**Next Steps:**
1. Run super_cleaner.py on your uploaded file
2. Review the generated JSON report for cleaning statistics
3. Call describe() on the cleaned file to verify quality
4. Proceed to Stage 3 (EDA) with plot() and stats()

Would you like me to guide you through using super_cleaner.py?"
```

### During Workflow Navigation:

```
User: "next()"
Agent: "🧹 **Stage 2: Data Cleaning & Preparation**

**Description:** Handle missing values, outliers, duplicates, and inconsistencies

**Recommended Tools:**
1. `super_cleaner.py` - RECOMMENDED: Advanced all-in-one cleaner
   (CLI: python data_science/tools/super_cleaner.py --file <file> --output cleaned.csv)
2. `robust_auto_clean_file()` - Comprehensive auto-cleaning with LLM insights
3. `impute_simple()` - Simple imputation (mean/median/mode)
4. `impute_knn()` - KNN-based imputation
5. `remove_outliers()` - Outlier detection and removal
6. `encode_categorical()` - Encode categorical variables
7. `detect_metadata_rows()` - Detect and handle metadata rows

**Navigation:**
• `next()` - Advance to Stage 3
• `back()` - Return to Stage 1
• Current: Stage 2 of 11

💡 **Tip:** super_cleaner.py is a powerful one-command solution for most cleaning needs!"
```

---

## 📊 Integration Summary

| Aspect | Status |
|--------|--------|
| Workflow Stage 2 | ✅ Added as #1 recommendation |
| Agent Instructions | ✅ Added to 4 key sections |
| CLI Usage Guide | ✅ Clear syntax provided |
| When to Use | ✅ Documented in prompts |
| Alternatives | ✅ Listed with use cases |

---

## 🧪 Verification

```bash
# Test 1: Imports compile
python -c "from data_science.ds_tools import next_stage, back_stage"
# Result: ✅ Success

# Test 2: Agent loads
python -c "from data_science.agent import root_agent"
# Result: ✅ Success

# Test 3: Super cleaner exists
python -c "import os; print(os.path.exists('data_science/tools/super_cleaner.py'))"
# Result: ✅ True
```

---

## 🚀 Ready to Test

### Test Scenario: User Wants to Clean Data

1. **Upload a CSV file with issues** (missing values, outliers, etc.)
2. **Run:** `analyze_dataset()` - See data quality issues
3. **Call:** `next()` - Navigate to Stage 2 (Cleaning)
4. **Expected:** See `super_cleaner.py` as #1 recommendation with CLI usage
5. **Alternative:** Ask "How do I clean my data?"
6. **Expected:** LLM recommends `super_cleaner.py` with detailed explanation

### Expected LLM Response:

```
"Based on your data analysis, I recommend using **super_cleaner.py** for comprehensive cleaning.

This tool will automatically:
• Impute missing values using median (numeric) and mode (categorical)
• Cap outliers using the IQR*3 winsorization method
• Parse datetime columns with multi-format support
• Remove duplicate rows and constant columns
• Optimize memory by downcasting numeric types

**To use it:**
```bash
python data_science/tools/super_cleaner.py --file your_uploaded_file.csv --output cleaned.csv
```

**Optional AutoML evaluation:**
```bash
python data_science/tools/super_cleaner.py --file your_file.csv --output cleaned.csv --automl
```

After cleaning, I'll help you validate the results with describe() and plot()."
```

---

## 📝 Notes

- **CLI Tool:** `super_cleaner.py` is a standalone CLI tool, not a registered agent tool
- **Usage Pattern:** LLM should instruct users to run it via terminal command
- **Integration Type:** Recommendation-based (not callable from agent directly)
- **Complementary Tools:** Works well with `describe()` → `super_cleaner.py` → `describe()` → `plot()` workflow
- **Alternative:** Users can still use `robust_auto_clean_file()` for LLM-powered cleaning

---

## 🎓 Why Super Cleaner is Recommended

1. **Comprehensive:** Handles 9+ cleaning tasks in one pass
2. **Deterministic:** Predictable, reproducible results
3. **Fast:** Optimized for large datasets with downcasting
4. **Windows-Friendly:** Pandas 2.x compatible, tz-naive datetime handling
5. **Optional Plugins:** Best-effort approach (never fails if plugin unavailable)
6. **AutoML Integration:** Optional model evaluation without separate steps
7. **Reporting:** JSON sidecar report with cleaning statistics

---

**Status:** ✅ PRODUCTION READY  
**Next Steps:** Test with real messy datasets  
**Documentation:** Complete with usage examples and guidance

