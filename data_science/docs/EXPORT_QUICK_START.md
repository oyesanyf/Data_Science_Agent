# PDF Export - Quick Start Guide

## ✅ The Tool Exists! It's called `export()`

**Important:** The tool is named **`export()`** not `export_analysis_to_pdf()`

## How to Use

### Basic Usage (Simplest)
```python
export()
```
That's it! This will:
- ✅ Automatically include ALL plots from your analysis
- ✅ Generate executive summary
- ✅ Include dataset statistics
- ✅ Create professional PDF report
- ✅ Upload to UI Artifacts panel

### With Custom Title
```python
export(title="My Analysis Report")
```

### With Custom Summary
```python
export(
    title="Sales Analysis Q4 2024",
    summary="Comprehensive analysis of Q4 sales data showing 23% growth in Region A with predictive models achieving 94% accuracy."
)
```

## Complete Workflow Example

```python
# 1. Upload your data (the UI does this automatically when you upload a CSV)

# 2. Analyze and visualize
analyze_dataset(csv_path='your_data.csv')
plot(csv_path='your_data.csv')

# 3. Train models (optional)
train(target='your_target_column', csv_path='your_data.csv')
explain_model(target='your_target_column')

# 4. Export everything to PDF
export(title="Complete Analysis Report")
```

## What Happens When You Run `export()`

1. **Collects all plots** from `data_science/.plot/` folder
2. **Generates PDF** with:
   - Title page
   - Executive summary
   - Dataset overview (rows, columns, types)
   - All visualizations with captions
   - Recommendations
3. **Saves locally** to `data_science/.export/report_<timestamp>.pdf`
4. **Uploads to UI** - Check the **Artifacts panel** 📄
5. **Returns details**:
   ```json
   {
     "message": "✅ PDF report generated successfully",
     "pdf_filename": "report_20251015_001234.pdf",
     "ui_location": "📄 Check the Artifacts panel",
     "plots_included": 12,
     "page_count": 8,
     "file_size_mb": 2.4
   }
   ```

## Where to Find Your PDF

### In the UI:
1. Look for the **Artifacts panel** (usually on right side)
2. Find your PDF: `report_<timestamp>.pdf`
3. Click to download 📥

### On Your Computer:
- Local path: `data_science\.export\report_<timestamp>.pdf`

## Common Questions

**Q: Do I need to specify which plots to include?**  
A: No! The tool automatically finds and includes ALL plots.

**Q: What if I have no plots?**  
A: The tool will still create a PDF with dataset info and recommendations.

**Q: Can I customize the report content?**  
A: Yes, use the `summary` parameter to add your own executive summary.

**Q: Where are the plots?**  
A: Any plots created by `plot()`, `analyze_dataset()`, `explain_model()`, etc. are automatically saved to `.plot/` and included.

**Q: Will it include SHAP plots?**  
A: Yes! All plots are included, including SHAP visualizations.

## Troubleshooting

### "No tool named export_analysis_to_pdf"
**Problem:** You used the wrong name  
**Solution:** Use `export()` not `export_analysis_to_pdf()`

### "0 plots included"
**Problem:** No visualizations were generated yet  
**Solution:** Run `plot()` or `analyze_dataset()` first

### "Can't find PDF in UI"
**Problem:** Artifact panel not visible  
**Solution:** Look for "Artifacts" tab/panel in the UI. The PDF will be listed with its timestamp filename.

## Example Messages You'll See

**When you run:**
```python
export(title="Housing Analysis")
```

**Agent will respond:**
> "✅ PDF report generated successfully: report_20251015_001234.pdf
> 
> Generated comprehensive 8-page PDF report with 12 visualizations. 
> **Report is available in the Artifacts panel** - look for 'report_20251015_001234.pdf'.
> 
> 📄 Check the Artifacts panel in the UI to download the PDF report"

**Then you:**
- Open Artifacts panel
- Click `report_20251015_001234.pdf`
- Download! 🎉

## Quick Reference

| Command | Description |
|---------|-------------|
| `export()` | Generate PDF with auto summary |
| `export(title="My Report")` | Custom title |
| `export(title="Report", summary="...")` | Custom title + summary |
| `help(command='export')` | Show detailed help |

## Server Status

✅ **Server is now running properly on port 8080**  
✅ **Export tool is loaded and ready to use**  
✅ **All 43 tools available**  

## Ready to Use!

Just run:
```python
export()
```

And your PDF report will be generated automatically! 🚀

