# How to Access PDF Reports in the UI

## ✅ Yes! PDFs are automatically available in the UI

When you use the `export()` tool, the generated PDF report is **automatically uploaded as an artifact** and appears in the **Artifacts panel** of the ADK web interface.

## Where to Find Your PDF

### 1. **Artifacts Panel** 📄
After running `export()`, look for the **Artifacts panel** in the UI (usually on the right side or in a tab).

### 2. **PDF Filename** 
The report will be listed with its timestamped filename:
```
report_20251015_001234.pdf
```

### 3. **Click to Download**
Click on the PDF artifact to download it to your computer.

## Example Workflow

### In the Chat:
```python
export(title="Sales Analysis Report")
```

### Agent Response Will Show:
```json
{
  "message": "✅ PDF report generated successfully: report_20251015_001234.pdf",
  "pdf_filename": "report_20251015_001234.pdf",
  "ui_location": "📄 Check the Artifacts panel in the UI to download the PDF report",
  "summary": "Generated comprehensive 8-page PDF report with 12 visualizations. 
             **Report is available in the Artifacts panel** - look for 'report_20251015_001234.pdf'. 
             Also saved to C:\\harfile\\data_science_agent\\data_science\\.export"
}
```

### The Agent Will Also Say:
> "Your PDF report `report_20251015_001234.pdf` is ready! Check the **Artifacts panel** in the UI to download it."

## What You'll See

### In the Chat Window:
- ✅ Success message with PDF filename
- 📊 Report statistics (pages, plots, file size)
- 📍 Clear instruction to check Artifacts panel
- 💾 Local file path for reference

### In the Artifacts Panel:
- 📄 PDF file with clickable download link
- 🕐 Timestamp in filename for easy identification
- 📥 One-click download

## Multiple Reports

If you generate multiple reports, they'll all appear in the Artifacts panel:
```
report_20251015_090000.pdf  (Morning analysis)
report_20251015_140000.pdf  (Afternoon update)
report_20251015_180000.pdf  (Final report)
```

Each one is clickable and downloadable separately.

## Local File Access

The PDF is **also saved locally** to:
```
data_science/.export/report_<timestamp>.pdf
```

You can access it directly from this folder if you prefer.

## Benefits

✅ **No need to search** - Artifact appears automatically  
✅ **One-click download** - Just click the PDF name  
✅ **Always accessible** - Stays in artifacts panel for the session  
✅ **Clear labeling** - Timestamped filenames prevent confusion  
✅ **Dual storage** - Available in UI and local folder  

## Technical Details

### How It Works:
1. `export()` generates PDF with ReportLab
2. PDF saved to `data_science/.export/`
3. PDF uploaded to ADK as artifact via `_save_artifact_rl()`
4. ADK UI displays it in Artifacts panel
5. User clicks to download

### Artifact Upload:
```python
artifact = types.Part(
    inline_data=types.Blob(
        mime_type="application/pdf",
        data=pdf_data
    )
)
await _save_artifact_rl(tool_context, filename=pdf_filename, artifact=artifact)
```

### Result Message:
The tool returns explicit information:
- `pdf_filename` - Exact name to look for
- `ui_location` - Clear instructions
- `artifact_saved` - Confirmation of upload
- `summary` - Human-readable message

## Troubleshooting

### Can't Find PDF in UI?
**Check:**
- Look for the "Artifacts" panel/tab (usually on right side)
- Verify the exact filename from the agent's response
- Refresh the page if needed
- Check local `.export` folder as backup

### PDF Not Uploading?
**If `artifact_saved: false`:**
- The PDF is still saved locally in `.export` folder
- Access it directly from: `data_science/.export/`
- This can happen if tool_context is unavailable

### Multiple PDFs?
**Each export creates a new file:**
- Timestamped filenames prevent overwriting
- All appear in Artifacts panel
- Download the one you need

## Summary

**Yes, the PDF URL/link is automatically available in the UI!**

The `export()` tool:
1. ✅ Generates professional PDF report
2. ✅ Saves to local `.export` folder
3. ✅ **Uploads to UI Artifacts panel**
4. ✅ Returns clear instructions on where to find it
5. ✅ Agent explicitly tells you the filename and location

**You just need to:**
1. Run `export()`
2. Read the agent's response for the filename
3. Click the PDF in the Artifacts panel
4. Download and share!

🎉 **It's that simple!**

