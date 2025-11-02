# data_science/example_ui_sink_tool.py
"""
Example tool demonstrating UI Sink capabilities.
This tool shows how to return rich UI blocks for automatic rendering.
"""
import pandas as pd
from typing import Dict, Any, List


def example_simple_ui_tool(message: str = "Hello from UI Sink!") -> Dict[str, Any]:
    """
    Example tool with simple UI output.
    
    Args:
        message: Message to display
        
    Returns:
        Dict with ui_text for automatic markdown rendering
    """
    return {
        "status": "success",
        "ui_text": f"## Simple UI Example\n\n{message}\n\nThis message was automatically rendered in the Session UI Page!"
    }


def example_table_ui_tool(rows: int = 5) -> Dict[str, Any]:
    """
    Example tool demonstrating table rendering.
    
    Args:
        rows: Number of rows to generate
        
    Returns:
        Dict with table_rows for automatic table rendering
    """
    # Generate sample data
    data_rows = [["ID", "Name", "Value", "Status"]]
    for i in range(1, rows + 1):
        data_rows.append([
            str(i),
            f"Item_{i}",
            f"{i * 10.5:.2f}",
            "Active" if i % 2 == 0 else "Inactive"
        ])
    
    return {
        "status": "success",
        "ui_text": f"Generated {rows} sample rows",
        "table_rows": data_rows
    }


def example_rich_ui_tool(dataset_name: str = "sample_data") -> Dict[str, Any]:
    """
    Example tool demonstrating rich UI blocks with multiple sections.
    
    Args:
        dataset_name: Name of the dataset to analyze
        
    Returns:
        Dict with explicit ui_blocks for precise control
    """
    # Simulate analysis
    sample_metrics = {
        "rows": 1000,
        "columns": 15,
        "missing_pct": 2.5,
        "duplicates": 3
    }
    
    # Simulate feature importance
    feature_rows = [
        ["Feature", "Importance", "Type"],
        ["age", "0.45", "numeric"],
        ["income", "0.32", "numeric"],
        ["education", "0.18", "categorical"],
        ["location", "0.05", "categorical"]
    ]
    
    # Return explicit UI blocks for precise layout
    return {
        "status": "success",
        "ui_blocks": [
            {
                "type": "markdown",
                "title": "Dataset Overview",
                "content": f"""
## {dataset_name}

This dataset contains **{sample_metrics['rows']:,}** rows and **{sample_metrics['columns']}** columns.

### Data Quality
- **Missing values**: {sample_metrics['missing_pct']}%
- **Duplicates**: {sample_metrics['duplicates']} rows

### Recommendations
1. [OK] Data quality is good
2. [WARNING]  Consider handling missing values
3.  Review duplicate rows
"""
            },
            {
                "type": "table",
                "title": "Feature Analysis",
                "rows": feature_rows
            },
            {
                "type": "markdown",
                "title": "Next Steps",
                "content": """
### Suggested Actions

1. **Data Cleaning**: Use `robust_auto_clean_file` to handle missing values
2. **Feature Engineering**: Create interaction features from top predictors
3. **Model Training**: Train with `smart_autogluon_automl` for best results
"""
            },
            {
                "type": "artifact_list",
                "title": "Generated Reports",
                "files": ["data_profile.html", "correlation_matrix.png", "distribution_plots.pdf"]
            }
        ]
    }


def example_metrics_ui_tool(model_name: str = "LightGBM") -> Dict[str, Any]:
    """
    Example tool demonstrating metrics rendering.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dict with metrics for automatic table rendering
    """
    return {
        "status": "success",
        "ui_text": f"## Model Training Complete: {model_name}\n\nModel trained successfully with the following performance metrics:",
        "metrics": {
            "Accuracy": "0.9542",
            "Precision": "0.9321",
            "Recall": "0.9654",
            "F1-Score": "0.9485",
            "AUC-ROC": "0.9876",
            "Training Time": "12.3s"
        },
        "artifacts": ["model.pkl", "feature_importance.png", "confusion_matrix.png", "roc_curve.png"]
    }


# Example of a tool that returns CSV for table rendering
def example_csv_table_ui_tool() -> Dict[str, Any]:
    """
    Example tool demonstrating CSV-to-table rendering.
    
    Returns:
        Dict with table_csv for automatic table rendering
    """
    csv_data = """Product,Sales,Growth
Widget A,15000,+12%
Widget B,23000,+8%
Widget C,8500,-3%
Widget D,31000,+25%"""
    
    return {
        "status": "success",
        "ui_text": "## Sales Report Q4 2024\n\nQuarterly sales performance by product line:",
        "table_csv": csv_data
    }


# Example combining all features
def example_comprehensive_ui_tool(analysis_type: str = "full") -> Dict[str, Any]:
    """
    Comprehensive example combining all UI sink features.
    
    Args:
        analysis_type: Type of analysis (full, quick, detailed)
        
    Returns:
        Dict with multiple UI blocks showcasing all capabilities
    """
    return {
        "status": "success",
        "ui_blocks": [
            {
                "type": "markdown",
                "title": f" {analysis_type.title()} Analysis Report",
                "content": f"""
# Data Science Analysis

**Analysis Type**: {analysis_type}  
**Timestamp**: 2025-10-22 18:45:00  
**Status**: [OK] Complete

---

## Executive Summary

This comprehensive analysis includes data profiling, feature engineering, model training, and evaluation.
"""
            },
            {
                "type": "table",
                "title": "Dataset Statistics",
                "rows": [
                    ["Metric", "Value"],
                    ["Total Rows", "10,000"],
                    ["Total Columns", "25"],
                    ["Missing Values", "2.3%"],
                    ["Duplicate Rows", "0"],
                    ["Memory Usage", "1.2 MB"]
                ]
            },
            {
                "type": "table",
                "title": "Model Performance",
                "rows": [
                    ["Model", "Accuracy", "F1-Score", "Training Time"],
                    ["LightGBM", "0.9542", "0.9485", "12.3s"],
                    ["XGBoost", "0.9521", "0.9467", "15.7s"],
                    ["CatBoost", "0.9498", "0.9432", "18.2s"],
                    ["Ensemble", "0.9587", "0.9521", "46.2s"]
                ]
            },
            {
                "type": "markdown",
                "title": "Key Findings",
                "content": """
###  Top Insights

1. **Best Model**: Ensemble achieves 95.87% accuracy
2. **Feature Importance**: Age and income are top predictors
3. **Data Quality**: Excellent - minimal missing values
4. **Performance**: Fast training times (<20s per model)

###  Recommendations

- Deploy the ensemble model for production
- Monitor feature drift on age and income
- Set up automated retraining pipeline
- Consider adding interaction features
"""
            },
            {
                "type": "artifact_list",
                "title": " Generated Artifacts",
                "files": [
                    "model_ensemble.pkl",
                    "feature_importance.png",
                    "confusion_matrix.png",
                    "roc_curves.png",
                    "learning_curves.png",
                    "shap_summary.png",
                    "full_report.html",
                    "model_card.pdf"
                ]
            },
            {
                "type": "markdown",
                "title": "Next Steps",
                "content": """
###  Deployment Checklist

- [ ] Review model card and documentation
- [ ] Test model on holdout dataset
- [ ] Set up monitoring dashboard
- [ ] Configure A/B testing framework
- [ ] Deploy to staging environment
- [ ] Run production validation tests
- [ ] Deploy to production
- [ ] Monitor performance metrics

**Estimated deployment time**: 2-3 days
"""
            }
        ]
    }
```

This example demonstrates the UI Sink system's capabilities and can be used as a template for creating rich, user-friendly tool outputs.

