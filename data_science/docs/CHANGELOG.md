# Changelog

All notable changes to the Data Science Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- PyPI package release
- Docker containerization
- Cloud deployment templates
- Advanced NLP tools
- Deep learning integration
- Real-time data streaming support

---

## [1.0.0] - 2025-01-15

### 🎉 Initial Release

The first stable release of Data Science Agent with comprehensive data science capabilities.

### Added

#### Core Features
- **44 Tools** across 14 categories for complete data science workflows
- **Google ADK Integration** - Built on Agent Development Kit framework
- **OpenAI GPT-4o** - Powered by LiteLLM for flexible LLM integration
- **FastAPI Web Interface** - Interactive web UI for agent interaction

#### AutoML Capabilities
- **AutoGluon Integration** (5 tools)
  - Smart AutoML with automatic chunking for large datasets
  - Time series forecasting with temporal validation
  - Automatic data cleaning and preprocessing
  - Multimodal support (text, images, tabular data)
  - Model listing and management

- **Auto-sklearn Implementation** (2 tools)
  - Automated classification with algorithm selection
  - Automated regression with hyperparameter optimization
  - Ensemble building and cross-validation

#### Machine Learning Tools (7 tools)
- Baseline model training with automatic evaluation
- Custom sklearn model training with 30+ algorithms
- Classification and regression specialized training
- Model persistence and loading by dataset
- Grid search hyperparameter tuning
- Comprehensive model evaluation
- Multi-method accuracy validation (CV, bootstrap, learning curves)
- Multi-model ensemble with voting

#### Data Analysis & Visualization (3 tools)
- Comprehensive exploratory data analysis
- 8 chart types (distribution, correlation, scatter, box, PCA, pairplot, time series, heatmap)
- Combined analysis and baseline modeling
- Automatic artifact management in UI

#### Model Explainability (1 tool)
- **SHAP Integration** - 5 plot types
  - Summary plots (global feature importance)
  - Bar charts (ranked feature importance)
  - Waterfall plots (individual prediction breakdown)
  - Dependence plots (feature interactions)
  - Force plots (prediction explanation)
- Automatic data preprocessing for SHAP compatibility

#### Statistics & Anomaly Detection (2 tools)
- **Statistical Analysis** with AI insights
  - Descriptive statistics
  - Normality tests (Shapiro-Wilk, Anderson-Darling)
  - Outlier detection (Z-score, IQR)
  - Correlation analysis
  - ANOVA testing

- **Anomaly Detection** with multiple methods
  - Isolation Forest
  - Local Outlier Factor (LOF)
  - Z-Score method
  - IQR method
  - AI-powered interpretation

#### Feature Engineering (11 tools)
- **Data Preprocessing**
  - Scaling (standard, minmax, robust)
  - Encoding (one-hot, label)
  - Polynomial and interaction features

- **Missing Data Handling**
  - Simple imputation (mean, median, mode)
  - K-Nearest Neighbors imputation
  - Iterative/MICE imputation

- **Feature Selection**
  - Statistical feature selection
  - Recursive Feature Elimination (RFE)
  - Sequential forward/backward selection

#### Clustering (4 tools)
- K-Means clustering
- DBSCAN (density-based)
- Hierarchical/agglomerative clustering
- Isolation Forest for outlier detection

#### Export & Reporting (1 tool)
- **PDF Report Generation** with ReportLab
  - Executive summary
  - Dataset information
  - All generated plots
  - AI-powered recommendations
  - Saved to `.export/` directory
  - Automatic artifact upload to UI

#### Model Management
- **Organized Model Storage** - `data_science/models/<dataset>/`
- **Model Loading** - Load models by dataset name
- **Multiple Models per Dataset** - Support for model versioning
- **Persistent Storage** - Models survive server restarts

#### Developer Tools
- **Runtime Code Validator** - Pre-flight checks for syntax and imports
- **Safe Startup Script** - Validation before server launch
- **Comprehensive Logging** - Debug-level logging for all components
- **Colorized Console Output** - Enhanced readability with colorlog

#### File Management (2 tools)
- List uploaded CSV files
- Save uploaded files to organized directories
- Automatic file handling for LiteLLM compatibility

#### Help & Discovery (3 tools)
- Comprehensive help system with all 44 tools
- Sklearn capabilities reference
- AI-powered next step suggestions

#### Text Processing (1 tool)
- TF-IDF feature extraction from text

### Fixed
- ✅ Logger undefined error in SHAP and export tools
- ✅ LiteLLM CSV upload compatibility with before_model_callback
- ✅ OpenAI tool call/response format validation
- ✅ SHAP data preprocessing for mixed-type datasets
- ✅ PCA sampling error with large datasets
- ✅ Empty DataFrame concatenation errors
- ✅ Windows console encoding for Unicode characters
- ✅ Port binding conflicts with background processes
- ✅ Async artifact saving for UI display
- ✅ Indentation and syntax validation

### Changed
- **Model Default** - Changed from GPT-4o-mini to GPT-4o for better quality
- **File Organization** - Moved uploads to `.uploaded/`, plots to `.plot/`, exports to `.export/`
- **AutoGluon Models** - Moved to `data_science/autogluon_models/` for better organization
- **Logging Level** - Set to DEBUG by default for comprehensive activity tracking
- **Agent Instructions** - Enhanced with proactive suggestions and clearer guidance

### Security
- Path traversal prevention
- File size limits
- ZIP bomb protection
- PII hashing in logs
- Formula injection detection

### Documentation
- Comprehensive README with 44 tools overview
- CONTRIBUTING.md with development guidelines
- 15+ specialized guides (SHAP, Export, Model Organization, etc.)
- Complete API reference
- Quick reference card
- Troubleshooting guide
- Code of conduct

---

## [0.5.0] - 2025-01-10

### Added
- Initial project structure
- Basic AutoGluon integration
- File upload handling
- Web interface setup

### Fixed
- Dependency installation issues
- Google Cloud Logging fallback
- Agent initialization errors

---

## [0.1.0] - 2025-01-01

### Added
- Project scaffolding
- Basic agent configuration
- Initial tool definitions

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-01-15 | First stable release with 44 tools |
| 0.5.0 | 2025-01-10 | Beta release with core functionality |
| 0.1.0 | 2025-01-01 | Initial alpha release |

---

## Contributors

Thank you to all contributors who made this project possible!

- **Core Development Team** - Initial implementation and architecture
- **Community Contributors** - Bug reports, feature requests, and improvements

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for a complete list.

---

## Release Notes Format

For future releases, use this format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security improvements
```

---

## Upgrade Instructions

### From 0.5.0 to 1.0.0

1. **Update dependencies**:
   ```bash
   uv sync
   ```

2. **Update environment variables**:
   ```bash
   $env:OPENAI_MODEL='gpt-4o'  # Default changed
   ```

3. **Migrate model files** (if applicable):
   ```bash
   # Models are now organized by dataset
   # Old: data_science/models/model.joblib
   # New: data_science/models/<dataset>/model.joblib
   ```

4. **Update file paths**:
   - Uploaded files: `.data/` → `.uploaded/`
   - Plots: root → `.plot/`
   - Exports: new `.export/` directory

5. **Restart server**:
   ```bash
   .\start_with_validation.ps1
   ```

---

## Support

For questions about specific versions:
- Check the [documentation](README.md)
- Open an [issue](https://github.com/yourusername/data-science-agent/issues)
- Join our [community](https://discord.gg/your-invite)

---

Last updated: 2025-01-15

