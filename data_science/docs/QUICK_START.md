# 🚀 Quick Start - Data Science Agent

## ⚡ 5-Minute Setup

### Step 1: Install UV (30 seconds)
```bash
# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Clone Project (1 minute)
```bash
git clone https://github.com/yourusername/data_science_agent.git
cd data_science_agent
```

### Step 3: Add API Key (1 minute)
```bash
# Copy template
copy .env.example .env     # Windows
cp .env.example .env       # Linux/Mac

# Edit .env file and add your key:
# OPENAI_API_KEY=sk-proj-your-actual-key-here
```

Get your OpenAI API key: https://platform.openai.com/api-keys

### Step 4: Start Server (2 minutes)
```bash
# Windows
.\start_server.ps1

# Linux/Mac  
python start_server.py
```

### Step 5: Use It! 🎉
Open browser: **http://localhost:8080**

---

## 📝 What Can You Do?

### Upload a CSV and ask:

```
"Analyze this dataset"
"Train a model to predict [target_column]"
"Generate an executive report"
"Show me feature importance"
"Clean this data"
"Find outliers"
```

### The agent has 80+ tools including:
- 📊 Data analysis & visualization
- 🤖 AutoML (AutoGluon, sklearn)
- 🧠 Model explainability (SHAP)
- 📄 PDF report generation
- 🔧 Feature engineering
- 📈 Statistical testing
- 🎯 Clustering & anomaly detection

---

## 🆘 Need Help?

**Full Installation Guide**: [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
- Detailed UV installation
- Troubleshooting
- GPU setup
- Development workflow

**Issues?**
```bash
# Port 8080 busy? Use startup script (auto-fixes)
.\start_server.ps1

# Missing dependencies?
uv sync

# API key not working?
# Check .env file has: OPENAI_API_KEY=sk-proj-...
```

---

## 🎯 First Analysis Example

1. **Upload** `tips.csv` (or any CSV)
2. **Ask**: `"Analyze this dataset and train a model to predict total_bill"`
3. **Wait** ~30 seconds
4. **Get**:
   - Full data analysis
   - Best model trained
   - Feature importance
   - Visualizations
   - Model file saved to `models/tips/`

---

## 📂 Where Are My Files?

```
data_science_agent/
├── data_science/
│   ├── .uploaded/          # Your uploaded CSVs
│   ├── .export/            # PDF reports
│   │   ├── tips/           # Organized by dataset!
│   │   └── housing/
│   ├── .plot/              # Generated charts
│   └── models/             # Trained models
│       ├── tips/           # Organized by dataset!
│       │   ├── baseline_model.joblib
│       │   └── autogluon/
│       └── housing/
```

---

## ⚙️ System Requirements

**Minimum:**
- Python 3.10+
- 8GB RAM
- 5GB disk space

**Recommended:**
- Python 3.12+
- 16GB RAM
- NVIDIA GPU (optional, for faster training)

---

## 🔑 API Keys

### Required:
- **OpenAI** (GPT-4): https://platform.openai.com/api-keys

### Optional:
- **Google Gemini** (fallback): https://ai.google.dev/

Add to `.env`:
```bash
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_API_KEY=AIzaSy-your-key-here  # Optional
```

---

## 💰 Cost Estimate

Using GPT-4o-mini (default):
- **Data analysis**: ~$0.01-0.05 per dataset
- **Model training**: Free (local)
- **Report generation**: ~$0.02-0.10 per report
- **Typical session**: ~$0.10-0.50

Using GPT-4o (optional, for complex tasks):
- ~10x higher cost, but much better quality

---

## 🚀 Next Steps

1. ✅ **Get it running** (5 minutes - follow steps above)
2. 📊 **Try an analysis** (upload CSV, ask questions)
3. 🤖 **Train a model** (let agent pick the best algorithm)
4. 📄 **Generate report** (professional PDF with charts)
5. 📖 **Read full guide** ([INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md))

---

**Questions?** Check [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for comprehensive docs!

**Ready?** Let's go! 🎉

```bash
.\start_server.ps1  # Windows
python start_server.py  # Linux/Mac
```

