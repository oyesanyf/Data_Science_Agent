# Data Science Agent with ADK

A comprehensive AI-powered data science platform with 150+ ML tools, streaming capabilities, and production-ready features.

## 🚀 Features

### Core Capabilities
- **150+ ML Tools**: Complete toolkit for data science, ML, and AI workflows
- **✅ 128 Reliable Tools**: Non-streaming tools for all data science workflows (streaming disabled to prevent auto-chaining conflicts)
- **Smart Workspace Management**: Organized per-dataset workspaces with artifact tracking
- **Unstructured Data Support**: Handle PDFs, images, documents, and more
- **Auto Analysis**: Automatic head/describe after data analysis
- **Executive Reports**: Professional PDF reports with visualizations
- **Hardened Artifact System**: Robust file handling with debouncing and error recovery

### Architecture
- **ADK-Safe Wrappers**: All tools use Google ADK compatibility layer
- **LiteLLM Integration**: OpenAI (primary) with Gemini fallback
- **Circuit Breaker Pattern**: Automatic failover and rate limit protection
- **Streaming Upload**: Handle files of any size without memory issues
- **Production-Ready**: Comprehensive error handling and logging

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Workspace Structure](#workspace-structure)
- [Available Tools](#available-tools)
- [File Upload](#file-upload)
- [Artifact Management](#artifact-management)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## 🎯 Quick Start

1. **Start the server**:
```bash
python start_server.py
```

2. **Open the UI**:
```
http://localhost:8080
```

3. **Upload your data**:
- Drag & drop CSV/Parquet files into the UI
- Files are automatically processed and a workspace is created

4. **Run analysis**:
```
analyze my data
plot the data
create executive report
```

## 📦 Installation

### Prerequisites
- Python 3.10+
- OpenAI API Key or Google Gemini API Key

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd data_science_agent
```

2. **Install dependencies** (automatic via `uv`):
```bash
python start_server.py
# Dependencies are automatically synced on first run
```

3. **Configure environment**:
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
OPENAI_API_KEY=sk-...
# or
GEMINI_API_KEY=...
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` |
| `GEMINI_API_KEY` | Google Gemini API key (optional) | - |
| `USE_GEMINI` | Enable Gemini fallback | `false` |
| `GENAI_MODEL` | Gemini model name | `gemini-2.0-flash-exp` |
| `ENABLE_UNSTRUCTURED` | Enable unstructured data processing | `false` |
| `UPLOAD_ROOT` | Root directory for uploads | `.uploaded` |
| `WORKSPACES_ROOT` | Root directory for workspaces | `{UPLOAD_ROOT}/_workspaces` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Model Selection

**Primary (Recommended): OpenAI**
- Fast, reliable, cost-effective
- Supports: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
```bash
export OPENAI_MODEL="gpt-4o-mini"  # Fast & cheap
export OPENAI_MODEL="gpt-4o"       # Best quality
```

**Fallback (Optional): Gemini**
- Requires `USE_GEMINI=true`
- Automatic failover with circuit breaker
```bash
export USE_GEMINI="true"
export GENAI_MODEL="gemini-2.0-flash-exp"
```

## 📁 Workspace Structure

Each dataset gets its own workspace with organized subdirectories:

```
.uploaded_workspaces/
└── {dataset_name}/
    └── {timestamp}/
        ├── uploads/        # Raw uploaded files
        ├── data/          # Processed datasets
        ├── plots/         # Generated visualizations
        ├── models/        # Trained ML models
        ├── reports/       # Executive reports (PDFs)
        ├── metrics/       # Performance metrics
        ├── indexes/       # Search indexes
        ├── logs/          # Execution logs
        ├── tmp/           # Temporary files
        ├── manifests/     # Metadata
        └── unstructured/  # PDFs, images, documents
```

### Workspace Features
- **Auto-creation**: Created on first file upload
- **Per-dataset isolation**: Each dataset has separate workspace
- **Artifact tracking**: All files tracked with versioning
- **Latest symlink**: Quick access to most recent workspace

## 🛠️ Available Tools

### Core Analysis (6 tools)
- `help` - Show available tools and usage
- `analyze_dataset` - Comprehensive EDA with auto head/describe
- `head` - Preview first rows of data
- `describe` - Statistical summary of data
- `plot` - Auto-generate visualizations
- `stats` - Statistical analysis

### Data Preprocessing (15+ tools)
- `scale_data` - Normalize/standardize features
- `encode_data` - Encode categorical variables
- `impute_simple` - Simple missing value imputation
- `impute_knn` - KNN-based imputation
- `impute_iterative` - Iterative imputation
- `select_features` - Feature selection
- `split_data` - Train/test splitting

### Machine Learning (40+ tools)
- `train_classifier` - Train classification models
- `train_regressor` - Train regression models
- `train_decision_tree` - Decision tree with visualization
- `ensemble` - Ensemble methods
- `grid_search` - Hyperparameter tuning
- `evaluate` - Model evaluation
- `predict` - Make predictions
- `explain_model` - SHAP explanations

### Advanced ML (20+ tools)
- `smart_autogluon_automl` - AutoML with AutoGluon
- `auto_sklearn_classify` - Auto-sklearn classification
- `optuna_tune` - Hyperparameter optimization
- `apply_pca` - Dimensionality reduction
- `smart_cluster` - Clustering analysis

### Time Series (10+ tools)
- `ts_prophet_forecast` - Facebook Prophet forecasting
- `sarimax_forecast` - SARIMAX models
- `arima_forecast` - ARIMA models
- `ts_backtest` - Backtesting

### Responsible AI (10+ tools)
- `fairness_report` - Fairness metrics
- `fairness_mitigation_grid` - Bias mitigation
- `drift_profile` - Data drift detection
- `causal_identify` - Causal inference
- `causal_estimate` - Treatment effect estimation

### Unstructured Data (3 tools)
- `process_unstructured` - Process PDFs, images, docs
- `list_unstructured` - List unstructured files
- `analyze_unstructured` - Analyze content

### Reporting (2 tools)
- `export_executive_report` - Generate PDF report
- `export` - Export to various formats

### ❌ Streaming Tools (DISABLED)
**Note:** Streaming tools were intentionally disabled because they auto-chain multiple operations, which conflicts with the interactive "one tool per response" workflow.

**Replaced with:** 128 reliable non-streaming tools that execute individually, allowing users to control the workflow step-by-step.

**Reason for disabling:** Tools like `stream_eda` would automatically call `analyze_dataset` → `describe` → `plot` → `stats` in sequence, causing looping issues and taking control away from the user.

**Alternative:** Use individual tools like `analyze_dataset_tool()`, `plot_tool_guard()`, `stats_tool_guard()`, etc. to build your workflow interactively.

## 📤 File Upload

### Supported Formats

**Structured Data**:
- CSV (auto-detected encoding)
- Parquet (columnar format)

**Unstructured Data** (requires `ENABLE_UNSTRUCTURED=true`):
- PDFs (text extraction, page counting)
- Images (JPG, PNG, GIF, BMP - dimension analysis)
- Documents (TXT, MD, DOC, DOCX)

### Upload Process

1. **Drag & drop** or use file picker in UI
2. **Automatic processing**:
   - CSV files streamed to disk (no memory limit)
   - Workspace created for dataset
   - File registered in artifact system
   - `default_csv_path` set in session
3. **Ready to analyze**: Tools automatically use uploaded file

### Large File Handling
- **No size limit**: Streaming upload prevents memory issues
- **Progress tracking**: Real-time upload progress
- **Error recovery**: Automatic retry on failure

## 🎨 Artifact Management

### Artifact Types
- `upload` - Original uploaded files
- `plot` - Generated visualizations (PNG)
- `report` - Executive reports (PDF)
- `model` - Trained models (pickle/joblib)
- `data` - Processed datasets
- `unstructured` - PDFs, images, documents

### Artifact Features
- **Automatic registration**: All generated files tracked
- **Versioning**: Multiple versions of same artifact
- **UI display**: Artifacts appear in UI Artifacts pane
- **Debouncing**: Prevents duplicate uploads
- **MIME detection**: Correct content types for all formats

### Artifact Guards

**Plot Tool Guard**:
- Ensures plots are always generated
- Fallback plots if tool fails
- Automatic registration and UI push
- Friendly chat messages

**Executive Report Guard**:
- Ensures PDF is always created
- Automatic registration and UI push
- Concise chat summaries

## 📚 API Reference

### Tool Invocation

**Via Chat**:
```
analyze my data
plot the data
train a classifier on target column
```

**Via Router**:
```python
route_user_intent_tool(
    action="analyze_dataset",
    params="{}"
)
```

**Direct Tool Call**:
```python
analyze_dataset_tool(
    csv_path="data.csv",
    tool_context=context
)
```

### Callback Hooks

**Before Model Callback**:
```python
_handle_file_uploads_callback(
    callback_context=context,
    llm_request=request
)
```
- Processes file uploads
- Converts CSV to text references
- Creates workspaces

**After Tool Callback**:
```python
after_tool_callback(
    tool=tool,
    tool_context=context,
    result=result
)
```
- Sanitizes results
- Promotes tool text to chat
- Auto-pushes artifacts

## 🔧 Troubleshooting

### Common Issues

**Issue**: `LiteLlm(BaseLlm) does not support this content part`
- **Solution**: Fixed by MIME type filtering in file upload callback
- Only images/videos/PDFs passed as inline_data
- Everything else converted to text references

**Issue**: `Workspace not initialized`
- **Solution**: Upload a file first to create workspace
- Or call `ensure_workspace` in tool

**Issue**: `ImportError: cannot import name 'head_tool'`
- **Solution**: Fixed by adding `head_tool` export to `adk_safe_wrappers.py`
- Server restart required after code changes

**Issue**: Plots not appearing in UI
- **Solution**: Use `plot_tool_guard` which ensures:
  - Files created and saved to workspace
  - Artifacts registered in system
  - Files pushed to UI Artifacts pane
  - Fallback plots if tool fails

**Issue**: Tool text not showing in chat
- **Solution**: `after_tool_callback` promotes `ui_text` to `reply_text`
- Auto-pushes any returned artifacts

### Debug Mode

Enable verbose logging:
```bash
export LOG_LEVEL=DEBUG
export LITELLM_LOG=DEBUG
```

Check logs:
```bash
# Application logs
tail -f data_science/logs/agent.log

# Server logs
# Look at terminal output
```

### Performance

**Slow startup**:
- First run syncs 150+ dependencies (normal)
- Subsequent runs skip sync (fast)

**Memory issues**:
- Use Parquet instead of CSV for large files
- Enable streaming for deep learning
- Clear `tmp/` directories periodically

## 👨‍💻 Development

### Project Structure

```
data_science_agent/
├── data_science/
│   ├── agent.py              # Main agent definition
│   ├── adk_safe_wrappers.py  # ADK-compatible tool wrappers
│   ├── ds_tools.py           # Core data science tools
│   ├── artifact_manager.py   # Workspace & artifact management
│   ├── artifact_utils.py     # Artifact helpers (MIME, push)
│   ├── callbacks.py          # Tool result callbacks
│   ├── routers.py            # Action routing
│   ├── plot_tool_guard.py    # Hardened plot wrapper
│   ├── executive_report_guard.py  # Hardened report wrapper
│   ├── head_describe_guard.py     # Head/describe wrappers
│   ├── auto_analysis_guard.py     # Auto head/describe
│   ├── unstructured_handler.py    # Unstructured data processing
│   ├── unstructured_tools.py      # Unstructured tool wrappers
│   └── streaming_*.py        # Streaming tool implementations
├── start_server.py           # Server entry point
├── main.py                   # Application main
└── README.md                 # This file
```

### Adding New Tools

1. **Implement tool** in `ds_tools.py`:
```python
async def my_new_tool(
    param: str,
    csv_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    # Your implementation
    return {"status": "success", "result": ...}
```

2. **Create ADK wrapper** in `adk_safe_wrappers.py`:
```python
def my_new_tool_wrapper(param: str = "", **kwargs) -> Dict[str, Any]:
    from .ds_tools import my_new_tool
    tool_context = kwargs.get("tool_context")
    return my_new_tool(param=param, tool_context=tool_context)
```

3. **Register tool** in `agent.py`:
```python
SafeFunctionTool(my_new_tool_wrapper)
```

4. **Add to registry** (optional) in `internal_registry.py`:
```python
TOOL_REGISTRY["my_new_tool"] = my_new_tool_wrapper
```

### Testing

```bash
# Run server in test mode
python start_server.py --test

# Check tool registration
curl http://localhost:8080/apps/data_science/tools

# Test specific tool
# Use UI at http://localhost:8080
```

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Support

[Add support contact information here]

---

**Built with**:
- [Google ADK](https://github.com/google/adk) - Agent Development Kit
- [LiteLLM](https://github.com/BerriAI/litellm) - LLM abstraction layer
- [Scikit-learn](https://scikit-learn.org/) - Machine learning
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [Matplotlib](https://matplotlib.org/) / [Seaborn](https://seaborn.pydata.org/) - Visualization
- [AutoGluon](https://auto.gluon.ai/) - AutoML
- [Prophet](https://facebook.github.io/prophet/) - Time series
- And 100+ more ML libraries!
