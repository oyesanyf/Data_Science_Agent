# ADK Placeholder Guide - Model Registry Integration

## Overview

ADK supports **built-in placeholder substitution** in agent instructions using `{}` syntax. This allows agents to dynamically reference:
- **Session State**: `{state.key}`, `{key}`, `{app:key}`, `{user:key}`
- **Artifacts**: `{artifact.filename}`

Our model registry now **fully leverages** this feature!

---

## 🎯 How It Works

### When You Train a Model

```python
# User trains a model
result = train_classifier_tool(target="price", model="RandomForest", ...)
```

**What Happens Automatically:**

1. **Model Binary Saved** → `RandomForest_price.joblib` (ADK artifact)
2. **Metadata JSON Saved** → `RandomForest_price_metadata.json` (ADK artifact, LLM-readable!)
3. **Session State Updated**:
   - `state.latest_model_name` = "RandomForest_price"
   - `state.latest_model_type` = "RandomForestClassifier"
   - `state.latest_model_target` = "price"
   - `state.latest_model_artifact` = "RandomForest_price.joblib"
   - `state.latest_model_metadata` = "RandomForest_price_metadata.json"
4. **Registry Entry Created** → Saved to `models/model_registry.json`
5. **Markdown Report** → `RandomForest_price_training.md`

---

## 📖 Using Placeholders in Agent Instructions

### Example 1: Reference Latest Model Info

```python
from google.adk.agents import Agent

evaluation_agent = Agent(
    name="model_evaluator",
    model="gemini-2.0-flash",
    instruction="""
    You just trained a {state.latest_model_type} model named '{state.latest_model_name}'.
    The target variable is: {state.latest_model_target}
    
    Please evaluate this model's performance and suggest improvements.
    """
)
```

**Output** (after training RandomForest for "price"):
```
You just trained a RandomForestClassifier model named 'RandomForest_price'.
The target variable is: price

Please evaluate this model's performance and suggest improvements.
```

### Example 2: Reference Model Metadata

```python
metadata_agent = Agent(
    name="metadata_reader",
    model="gemini-2.0-flash",
    instruction="""
    Here is the metadata for the latest trained model:
    
    {artifact.{state.latest_model_metadata}}
    
    Summarize the model's performance metrics.
    """
)
```

**What ADK Does:**
1. Replaces `{state.latest_model_metadata}` → `RandomForest_price_metadata.json`
2. Loads artifact `RandomForest_price_metadata.json`
3. Injects its content into the instruction

**LLM Sees:**
```json
Here is the metadata for the latest trained model:

{
  "model_name": "RandomForest_price",
  "model_type": "RandomForestClassifier",
  "target": "price",
  "metrics": {
    "accuracy": 0.95,
    "f1_score": 0.93
  },
  "registered_at": "2025-10-28T12:30:00",
  "artifact_name": "RandomForest_price.joblib",
  "version": 0
}

Summarize the model's performance metrics.
```

### Example 3: Reference Specific Model

```python
specific_model_agent = Agent(
    name="specific_evaluator",
    model="gemini-2.0-flash",
    instruction="""
    Load the metadata for the XGBoost model:
    
    {artifact.XGBoost_sales_metadata.json}
    
    Compare it to the Random Forest model:
    
    {artifact.RandomForest_sales_metadata.json}
    
    Which model performs better?
    """
)
```

---

## 🔧 Advanced Usage

### Optional Placeholders (Graceful Fallback)

Use `?` suffix for optional placeholders that won't break if missing:

```python
instruction = """
Latest model: {state.latest_model_name?}
Previous model: {state.previous_model_name?}

If previous model exists, compare them.
"""
```

### App-Level and User-Level State

```python
# App-level (shared across all users)
instruction = "Company name: {app:company_name}"

# User-level (shared across user's sessions)
instruction = "User preference: {user:default_model_type}"

# Session-level (current session only)
instruction = "Current model: {state.latest_model_name}"
```

---

## 📦 What Gets Saved as Artifacts

### For Each Trained Model:

| Artifact | Type | Purpose | Placeholder Example |
|----------|------|---------|-------------------|
| `ModelName.joblib` | Binary | Model file | N/A (binary, not LLM-readable) |
| `ModelName_metadata.json` | JSON | LLM-readable summary | `{artifact.ModelName_metadata.json}` |
| `ModelName_training.md` | Markdown | Human report | `{artifact.ModelName_training.md}` |

### JSON Metadata Structure

```json
{
  "model_name": "RandomForest_price",
  "model_type": "RandomForestClassifier",
  "target": "price",
  "metrics": {
    "accuracy": 0.9523,
    "precision": 0.9456,
    "recall": 0.9489,
    "f1_score": 0.9472
  },
  "registered_at": "2025-10-28T12:30:45",
  "artifact_name": "RandomForest_price.joblib",
  "version": 0,
  "instructions": "Use {artifact.RandomForest_price.joblib} to reference this model in agent prompts"
}
```

---

## 🚀 Real-World Example: Multi-Agent Workflow

```python
from google.adk.agents import Agent, AgentOrchestrator

# Agent 1: Train model (updates session.state automatically)
trainer = Agent(
    name="trainer",
    model="gemini-2.0-flash",
    instruction="Train a classifier on the uploaded dataset. Use RandomForest.",
    tools=[train_classifier_tool]
)

# Agent 2: Evaluate using placeholders
evaluator = Agent(
    name="evaluator",
    model="gemini-2.0-flash",
    instruction="""
    The model '{state.latest_model_name}' was just trained.
    
    Here are its metrics:
    {artifact.{state.latest_model_metadata}}
    
    Evaluate if accuracy > 0.90. If yes, recommend deployment. If no, suggest hyperparameter tuning.
    """
)

# Agent 3: Report generator
reporter = Agent(
    name="reporter",
    model="gemini-2.0-flash",
    instruction="""
    Create an executive summary based on:
    
    Model: {state.latest_model_name}
    Type: {state.latest_model_type}
    Target: {state.latest_model_target}
    
    Full training report:
    {artifact.{state.latest_model_name}_training.md}
    """
)

# Orchestrate
orchestrator = AgentOrchestrator([trainer, evaluator, reporter])
```

---

## ✅ Benefits

1. **No Manual String Formatting** - ADK handles it
2. **Type-Safe** - Artifacts loaded with proper MIME types
3. **Version Control** - ADK tracks artifact versions
4. **Production Ready** - Works with GCS in production
5. **LLM-Friendly** - Agents can "see" structured data
6. **Maintainable** - Change placeholder, not code

---

## 🧪 Testing Placeholders

```python
# After training a model:
assert tool_context.state['latest_model_name'] == "RandomForest_price"

# Check artifacts exist:
artifacts = await tool_context.list_artifacts()
assert "RandomForest_price.joblib" in artifacts
assert "RandomForest_price_metadata.json" in artifacts

# Load metadata:
metadata_part = await tool_context.load_artifact("RandomForest_price_metadata.json")
metadata = json.loads(metadata_part.text)
assert metadata["model_type"] == "RandomForestClassifier"
```

---

## 📚 References

- ADK Placeholders: [Article by YAMASAKI Masahide](https://dev.to/yamasakim/smarter-google-adk-prompts-inject-state-and-artifact-data-dynamically-4lld)
- ADK Artifacts: [Chapter 18 - Artifact Management](https://amulyabhatia.com/posts/adk/chapter-18-artifact-management/)
- Source: `google.adk.agents.instructions._populate_values`

---

**Status**: ✅ Fully Implemented
**All model training tools automatically create:**
- Binary artifacts (`.joblib`)
- Metadata artifacts (`.json`) - LLM-readable!
- Session state entries - placeholder-ready!
- Markdown reports (`.md`)

