# PDF Export Tool Guide

## Overview

The `export()` tool generates comprehensive PDF reports containing all your data science analyses, visualizations, and insights.

## Features

✅ **Executive Summary** - Auto-generated or custom summary of analyses  
✅ **Dataset Overview** - Complete statistics and column information  
✅ **All Visualizations** - Automatically includes all generated plots  
✅ **Professional Formatting** - Styled PDF with headers, tables, and charts  
✅ **Recommendations** - Built-in actionable next steps  
✅ **Automatic Artifact** - Saves to `.export` folder and uploads to UI  

## Usage

### Basic Usage
```python
export()
```

### Custom Title
```python
export(title="Housing Price Analysis Report")
```

### With Custom Summary
```python
export(
    title="Customer Segmentation Analysis",
    summary="Analyzed 50,000 customer records using K-means clustering and identified 5 distinct customer segments with actionable insights for marketing campaigns."
)
```

### With Specific Dataset
```python
export(
    title="Sales Forecast Report",
    csv_path="sales_data.csv",
    summary="Time series analysis of 3 years of sales data with predictive models."
)
```

## What's Included

The PDF report automatically includes:

### 1. Title Page
- Report title (customizable)
- Generation date and time
- Professional formatting

### 2. Executive Summary
- **Auto-generated**: Summarizes dataset size, features, and visualizations
- **Custom**: Use your own summary text for personalized reports

### 3. Dataset Overview
- Total rows and columns
- Memory usage statistics
- Missing value counts
- Column type breakdown (numeric, categorical, datetime)
- List of all columns

### 4. Visualizations & Charts
All plots from the `.plot` folder are automatically included:
- Correlation heatmaps
- Distribution plots
- Time series charts
- Scatter plots
- Box plots
- SHAP plots
- Statistical analysis charts
- Any custom visualizations

Each plot includes:
- Figure number
- Descriptive title
- Properly scaled image

### 5. Recommendations & Next Steps
Standard recommendations including:
- Data quality monitoring
- Feature engineering suggestions
- Model validation approaches
- Ensemble methods
- SHAP interpretability
- Model retraining strategies

### 6. Footer
Professional footer with generation details

## Output

The `export()` function returns:

```json
{
  "message": "PDF report generated successfully: report_20251015_120345.pdf",
  "pdf_path": "C:\\harfile\\data_science_agent\\data_science\\.export\\report_20251015_120345.pdf",
  "page_count": 8,
  "plots_included": 12,
  "file_size_mb": 2.4,
  "export_location": "C:\\harfile\\data_science_agent\\data_science\\.export",
  "artifact_saved": true,
  "summary": "Generated comprehensive 8-page PDF report with 12 visualizations. Report saved to .export folder and uploaded as artifact."
}
```

## File Location

PDFs are saved to: `data_science/.export/report_<timestamp>.pdf`

Example: `report_20251015_120345.pdf`

## Best Practices

### 1. Generate Plots First
Run your analyses and generate plots before exporting:
```python
# Generate visualizations
plot(csv_path='data.csv')
analyze_dataset(csv_path='data.csv')
explain_model(target='price', csv_path='data.csv')

# Then export everything
export(title="Complete Analysis Report")
```

### 2. Custom Summary for Stakeholders
Provide business context in your summary:
```python
export(
    title="Q4 Sales Analysis",
    summary="This analysis examines Q4 sales performance across 10 regions. Key findings show 23% growth in Region A driven by new product launches. The predictive model achieved 94% accuracy for next quarter forecasting, recommending increased inventory for high-demand products."
)
```

### 3. Multiple Reports
Generate different reports for different audiences:
```python
# Technical report for data science team
export(title="Technical Model Report", summary="Detailed technical analysis...")

# Executive report for management
export(title="Executive Summary", summary="High-level business insights...")
```

## Workflow Example

Complete workflow with export:

```python
# 1. Load and explore data
list_data_files()
analyze_dataset(csv_path='customers.csv')
plot(csv_path='customers.csv')

# 2. Clean and prepare
clean(csv_path='customers.csv')

# 3. Train models
train(target='churn', csv_path='customers.csv')
explain_model(target='churn')

# 4. Generate comprehensive report
export(
    title="Customer Churn Analysis Report",
    summary="Analyzed 100,000 customer records to predict churn. The gradient boosting model achieved 92% accuracy. SHAP analysis revealed that contract length and customer service calls are the top predictive factors. Recommendations include proactive outreach for at-risk customers."
)
```

## Technical Details

### Dependencies
- **reportlab**: PDF generation
- **Pillow**: Image processing

### File Format
- **Page Size**: US Letter (8.5" x 11")
- **Margins**: 1 inch all sides
- **Fonts**: Helvetica family
- **Images**: Auto-scaled to fit page
- **Colors**: Professional blue theme

### Performance
- Typical generation time: 1-3 seconds
- Handles 50+ plots efficiently
- Memory efficient (streams to disk)

## Troubleshooting

### No Plots Included
**Problem**: Report shows "0 plots included"  
**Solution**: Run visualization tools first (`plot()`, `explain_model()`, etc.)

### Large File Size
**Problem**: PDF is too large (>50 MB)  
**Solution**: Reports with many high-resolution plots may be large. This is normal for comprehensive analyses.

### Missing Data
**Problem**: Dataset statistics not showing  
**Solution**: Pass `csv_path` parameter or ensure a dataset is loaded

### Custom Summary Not Showing
**Problem**: Your custom summary isn't in the PDF  
**Solution**: Make sure you're passing the `summary` parameter correctly as a string

## Advanced Usage

### Programmatic Report Generation
Generate reports for multiple datasets:

```python
datasets = ['sales_2021.csv', 'sales_2022.csv', 'sales_2023.csv']

for dataset in datasets:
    year = dataset.split('_')[1].split('.')[0]
    
    # Analyze
    analyze_dataset(csv_path=dataset)
    plot(csv_path=dataset)
    
    # Export
    export(
        title=f"Sales Analysis {year}",
        csv_path=dataset,
        summary=f"Comprehensive analysis of sales data for {year}."
    )
```

### Scheduled Reports
Combine with scheduling tools to generate automated reports:
```python
# In a scheduled script
export(
    title="Daily ML Model Performance",
    summary=f"Automated daily report generated on {datetime.now().strftime('%Y-%m-%d')}."
)
```

## Summary

The `export()` tool is your one-stop solution for creating professional data science reports. It automatically collects all your analyses, plots, and insights into a beautiful PDF that's ready to share with stakeholders, managers, or clients.

**Key Benefits:**
- ⚡ **Fast**: Generates in seconds
- 📊 **Comprehensive**: Includes everything automatically
- 🎨 **Professional**: Styled and formatted beautifully
- 🔄 **Flexible**: Custom summaries and titles
- 📤 **Shareable**: Saves locally and uploads as artifact

---

**Next Steps:**  
Try it now! Run `export()` after your next analysis to see the power of automated reporting.

