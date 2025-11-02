# ============================================================================
# SEQUENTIAL WORKFLOW STAGE DEFINITIONS
# 14-Stage Professional Data Science Workflow
# ============================================================================

WORKFLOW_STAGES = [
    {
        "id": 1,
        "name": "Data Collection & Initial Analysis",
        "icon": "📥",
        "description": "Upload data and perform initial analysis",
        "tools": [
            {"name": "analyze_dataset_tool()", "description": "🔍 **START HERE!** Comprehensive dataset analysis with preview, statistics, and data quality assessment"},
            {"name": "list_data_files_tool()", "description": "List all available CSV files in your workspace"},
            {"name": "head_tool_guard()", "description": "Preview the first 5 rows of your dataset"},
            {"name": "shape_tool()", "description": "Quick dataset dimensions (rows × columns)"},
        ],
        "tip": "Most users start with **analyze_dataset_tool()** to get a complete overview"
    },
    {
        "id": 2,
        "name": "Data Cleaning & Preparation",
        "icon": "🧹",
        "description": "Handle missing values, outliers, duplicates, and inconsistencies",
        "tools": [
            {"name": "robust_auto_clean_file_tool()", "description": "Advanced auto-cleaning (outliers, missing values, types, headers)"},
            {"name": "describe_tool_guard()", "description": "Detailed statistical summary after cleaning"},
            {"name": "impute_simple_tool()", "description": "Simple imputation for missing values"},
            {"name": "impute_knn_tool()", "description": "KNN-based imputation"},
            {"name": "remove_outliers_tool()", "description": "Outlier detection and removal"},
            {"name": "encode_categorical_tool()", "description": "Encode categorical variables"},
        ],
        "tip": "Clean your data before analysis and modeling"
    },
    {
        "id": 3,
        "name": "Exploratory Data Analysis (EDA)",
        "icon": "🔍",
        "description": "Understand data distributions, patterns, and relationships",
        "tools": [
            {"name": "plot_tool()", "description": "Generate automatic visualizations (8 chart types)"},
            {"name": "stats_tool()", "description": "AI-powered statistical analysis"},
            {"name": "correlation_analysis_tool()", "description": "Correlation matrix and relationship discovery"},
            {"name": "describe_tool_guard()", "description": "Statistical summary of numerical features"},
        ],
        "tip": "Explore your data to discover patterns and insights"
    },
    {
        "id": 4,
        "name": "Visualization",
        "icon": "📊",
        "description": "Create plots, charts, and visual representations",
        "tools": [
            {"name": "plot_tool()", "description": "Automatic multi-chart visualization"},
            {"name": "correlation_plot_tool()", "description": "Correlation heatmap"},
            {"name": "plot_distribution_tool()", "description": "Distribution plots for all features"},
        ],
        "tip": "Visualize patterns for better understanding and presentations"
    },
    {
        "id": 5,
        "name": "Feature Engineering",
        "icon": "⚙️",
        "description": "Create, select, and transform features",
        "tools": [
            {"name": "select_features_tool()", "description": "Automated feature selection"},
            {"name": "expand_features_tool()", "description": "Generate polynomial and interaction features"},
            {"name": "auto_feature_synthesis_tool()", "description": "AI-powered feature synthesis"},
            {"name": "apply_pca_tool()", "description": "Principal Component Analysis"},
        ],
        "tip": "Engineer features to improve model performance"
    },
    {
        "id": 6,
        "name": "Statistical Analysis",
        "icon": "📈",
        "description": "Hypothesis testing and statistical inference",
        "tools": [
            {"name": "stats_tool()", "description": "Comprehensive statistical analysis"},
            {"name": "correlation_analysis_tool()", "description": "Correlation and relationships"},
            {"name": "hypothesis_test_tool()", "description": "Statistical hypothesis testing"},
        ],
        "tip": "Validate assumptions and test hypotheses scientifically"
    },
    {
        "id": 7,
        "name": "Machine Learning Model Development",
        "icon": "🤖",
        "description": "Train and tune machine learning models",
        "tools": [
            {"name": "recommend_model_tool()", "description": "AI-powered model recommendations (auto-detects target)"},
            {"name": "train_classifier_tool()", "description": "Train classification models"},
            {"name": "train_regressor_tool()", "description": "Train regression models"},
            {"name": "smart_autogluon_automl()", "description": "AutoML training (best for most cases)"},
            {"name": "train_lightgbm_tool()", "description": "LightGBM model training"},
            {"name": "train_xgboost_tool()", "description": "XGBoost model training"},
        ],
        "tip": "Start with AutoML for best automatic results"
    },
    {
        "id": 8,
        "name": "Model Evaluation & Validation",
        "icon": "✅",
        "description": "Assess model performance with metrics and validation",
        "tools": [
            {"name": "evaluate_tool()", "description": "Comprehensive model evaluation"},
            {"name": "accuracy_tool()", "description": "Calculate accuracy metrics"},
            {"name": "explain_model_tool()", "description": "Model explainability (SHAP values)"},
            {"name": "feature_importance_tool()", "description": "Feature importance analysis"},
            {"name": "cross_validate_tool()", "description": "K-fold cross-validation"},
        ],
        "tip": "MANDATORY after training! Never skip evaluation"
    },
    {
        "id": 9,
        "name": "Prediction & Inference",
        "icon": "🎯",
        "description": "Make predictions on new data",
        "tools": [
            {"name": "predict_tool()", "description": "Make predictions with trained model"},
            {"name": "predict_proba_tool()", "description": "Prediction probabilities"},
            {"name": "batch_predict_tool()", "description": "Batch predictions on multiple files"},
        ],
        "tip": "Use your trained model to make predictions"
    },
    {
        "id": 10,
        "name": "Model Deployment (Optional)",
        "icon": "🚀",
        "description": "Deploy models as APIs or services",
        "tools": [
            {"name": "export_model_tool()", "description": "Export model for deployment"},
            {"name": "save_model_tool()", "description": "Save model to disk"},
            {"name": "load_model_tool()", "description": "Load existing model"},
        ],
        "tip": "Deploy your model for production use"
    },
    {
        "id": 11,
        "name": "Report and Insights",
        "icon": "📝",
        "description": "Summarize findings and business implications",
        "tools": [
            {"name": "generate_insights_tool()", "description": "AI-powered insights generation"},
            {"name": "summary_report_tool()", "description": "Comprehensive analysis summary"},
        ],
        "tip": "Document your findings and insights"
    },
    {
        "id": 12,
        "name": "Others (Specialized Methods)",
        "icon": "🔬",
        "description": "Domain-specific and advanced techniques",
        "tools": [
            {"name": "time_series_analysis_tool()", "description": "Time series analysis"},
            {"name": "clustering_tool()", "description": "Unsupervised clustering"},
            {"name": "anomaly_detection_tool()", "description": "Detect anomalies"},
        ],
        "tip": "Apply specialized methods for specific domains"
    },
    {
        "id": 13,
        "name": "Executive Report",
        "icon": "📊",
        "description": "Generate executive summary with key findings",
        "tools": [
            {"name": "export_executive_report_tool()", "description": "AI-powered executive summary PDF"},
        ],
        "tip": "Create a high-level summary for stakeholders"
    },
    {
        "id": 14,
        "name": "Export Report as PDF",
        "icon": "📄",
        "description": "Export comprehensive technical reports",
        "tools": [
            {"name": "export_reports_for_latest_run_pathsafe()", "description": "Comprehensive technical report PDF"},
        ],
        "tip": "Export detailed technical documentation"
    },
]


def get_stage(stage_id: int) -> dict:
    """Get stage definition by ID."""
    for stage in WORKFLOW_STAGES:
        if stage["id"] == stage_id:
            return stage
    return WORKFLOW_STAGES[0]  # Default to stage 1


def get_next_stage(current_stage: int) -> dict:
    """Get the next stage in the workflow."""
    next_id = current_stage + 1 if current_stage < 14 else 14
    return get_stage(next_id)


def format_stage_menu(stage: dict) -> str:
    """
    Format a single stage as a menu with improved formatting for all contexts.
    Creates clean, well-aligned output that works in chat, logs, and markdown files.
    """
    lines = []
    
    # Header with stage info
    lines.append(f"## 📋 WORKFLOW STAGE {stage['id']}: {stage['icon']} {stage['name']}")
    lines.append("")
    lines.append(f"{stage['description']}")
    lines.append("")
    
    # Tools list
    if stage['tools']:
        lines.append("### Available Tools:")
        lines.append("")
        for i, tool in enumerate(stage['tools'], 1):
            tool_name = tool['name']
            tool_desc = tool['description']
            lines.append(f"{i}. `{tool_name}` - {tool_desc}")
        lines.append("")
    
    # Tip
    if stage.get('tip'):
        lines.append(f"💡 **TIP:** {stage['tip']}")
        lines.append("")
    
    # Progress footer
    lines.append("---")
    lines.append("")
    lines.append(f"🚀 Progress: Stage {stage['id']} of 14")
    
    # Next step (always complete sentence)
    next_stage = stage['id'] + 1 if stage['id'] < 14 else 14
    if stage['id'] < 14:
        lines.append(f"➡️ Next: Type `next()` to see Stage {next_stage}")
    else:
        lines.append(f"✅ This is the final stage! Export your reports when ready.")
    
    # Join all lines with single newlines (cleaner output)
    return "\n".join(lines)


def get_stage_for_tool(tool_name: str) -> int:
    """Determine which stage a tool belongs to (for auto-advancement)."""
    tool_name_lower = tool_name.lower()
    
    # Stage 1: Data Collection & Initial Analysis
    if any(keyword in tool_name_lower for keyword in ['analyze_dataset', 'list_data', 'head', 'shape']):
        return 1
    
    # Stage 2: Data Cleaning
    if any(keyword in tool_name_lower for keyword in ['clean', 'impute', 'outlier', 'encode', 'normalize', 'standardize']):
        return 2
    
    # Stage 3: EDA
    if any(keyword in tool_name_lower for keyword in ['stats', 'correlation', 'describe']):
        return 3
    
    # Stage 4: Visualization
    if any(keyword in tool_name_lower for keyword in ['plot', 'visualiz']):
        return 4
    
    # Stage 5: Feature Engineering
    if any(keyword in tool_name_lower for keyword in ['feature', 'pca', 'select', 'expand']):
        return 5
    
    # Stage 14: Export PDF
    if 'export_reports_for_latest_run_pathsafe' in tool_name_lower:
        return 14

    # Stage 6: Statistical Analysis
    if any(keyword in tool_name_lower for keyword in ['hypothesis', 'test', 'statistical']):
        return 6
    
    # Stage 7: Model Development
    if any(keyword in tool_name_lower for keyword in ['train', 'automl', 'recommend_model']):
        return 7
    
    # Stage 8: Evaluation
    if any(keyword in tool_name_lower for keyword in ['evaluate', 'accuracy', 'explain', 'importance', 'cross_validate']):
        return 8
    
    # Stage 9: Prediction
    if any(keyword in tool_name_lower for keyword in ['predict']):
        return 9
    
    # Stage 10: Deployment
    if any(keyword in tool_name_lower for keyword in ['deploy', 'export_model', 'save_model']):
        return 10
    
    # Stage 13: Executive Report
    if 'executive' in tool_name_lower:
        return 13
    
    # Stage 14: Export PDF
    if 'export_report' in tool_name_lower:
        return 14
    
    return 0  # Unknown

