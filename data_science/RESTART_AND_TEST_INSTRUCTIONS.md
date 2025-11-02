# 🔄 RESTART SERVER & TEST PROPERLY

## Current Problems:

1. ✅ **Files ARE being created** - Found in `reports/` folders
2. ❌ **Plot tool never ran** - Blocked by one-tool-per-turn policy
3. ❌ **Multiple workspaces active** - 8+ different workspace folders
4. ❌ **404 errors** - ADK trying to fetch from HTTP (expected, not configured)

---

## ⚠️ CRITICAL: RESTART SERVER

**All recent fixes require restart to take effect:**

```bash
# Stop server (Ctrl+C)
cd C:\harfile\data_science_agent
python -m data_science.main
```

### Why Restart?
- ✅ Applies `tools_logger` bug fix
- ✅ Clears all session state
- ✅ Resets workspace management
- ✅ Loads updated code

---

## 📋 PROPER TESTING PROCEDURE

### Step 1: Upload ONE Dataset

```
1. Upload a SINGLE CSV file (e.g., tips.csv)
2. Wait for Stage 1 menu to display
3. Note the workspace folder created
```

**Expected:**
```
Workspace: .uploaded/_workspaces/tips/20251101_HHMMSS/
```

---

### Step 2: Run ONE Tool at a Time

❌ **DON'T DO THIS:**
```
User: "Analyze the dataset, clean it, and create plots"
→ LLM tries to run 3 tools
→ Only first tool succeeds
→ Others blocked by one-tool-per-turn ❌
```

✅ **DO THIS INSTEAD:**
```
User: "Analyze the dataset"
→ analyze_dataset_tool() runs ✅
→ Wait for completion
→ Check results

User: "Now clean the data"
→ robust_auto_clean_file_tool() runs ✅
→ Wait for completion
→ Check results

User: "Create plots"
→ plot_tool() runs ✅
→ Wait for completion
→ Check plots folder
```

---

### Step 3: Verify Files Created

After EACH tool execution:

```powershell
cd C:\harfile\data_science_agent\data_science\.uploaded\_workspaces

# Find your workspace (replace 'tips' with your dataset name)
ls tips/*/reports/
ls tips/*/results/
ls tips/*/plots/
```

**Expected for analyze_dataset_tool:**
```
tips/20251101_HHMMSS/
  ├─ reports/
  │   └─ 20251101_HHMMSS_analyze_dataset_tool.md  ✅
  └─ results/
      └─ analyze_dataset_tool_output.json          ✅
```

**Expected for plot_tool:**
```
tips/20251101_HHMMSS/
  ├─ reports/
  │   └─ 20251101_HHMMSS_plot_tool.md  ✅
  ├─ results/
  │   └─ plot_tool_output.json         ✅
  └─ plots/
      ├─ correlation_plot.png          ✅
      ├─ distribution_plot.png         ✅
      └─ scatter_matrix.png            ✅
```

---

## 🐛 Ignore These (Not Bugs):

### 1. "One-tool-per-turn policy" Message
```
⛔ One-tool-per-turn policy: a tool already ran in this assistant turn.
```
**This is CORRECT!** Just run tools one at a time.

### 2. 404 Errors in Logs
```
GET /apps/data_science/users/user/reports/xxx.md HTTP/1.1" 404 Not Found
```
**This is EXPECTED!** ADK artifact service is not configured. Files are saved to filesystem instead.

### 3. Multiple Workspace Folders
```
uploaded/20251101_160905/
uploaded/20251101_161027/
uploaded/20251101_161335/
```
**These are from BEFORE restart.** After restart with ONE dataset, you'll only have ONE active workspace folder.

---

## 🧪 Complete Test Sequence

```
1. RESTART SERVER ⚠️

2. Upload tips.csv (or any CSV)
   → Verify: Stage 1 menu shows
   → Verify: Workspace created at tips/20251101_HHMMSS/

3. Run: analyze_dataset_tool()
   → Wait for completion
   → Check: reports/xxx_analyze_dataset_tool.md exists
   → Check: results/analyze_dataset_tool_output.json exists

4. Run: describe_tool_guard()
   → Wait for completion
   → Check: reports/xxx_describe_tool_guard.md exists
   → Check: results/describe_tool_guard_output.json exists

5. Run: plot_tool()
   → Wait for completion
   → Check: reports/xxx_plot_tool.md exists
   → Check: results/plot_tool_output.json exists
   → Check: plots/*.png files exist ✅

6. Run: train_classifier(target='target_column')
   → Wait for completion
   → Check: reports/xxx_train_classifier.md exists
   → Check: results/train_classifier_output.json exists
   → Check: models/*.pkl file exists ✅

7. List all files:
   ```powershell
   Get-ChildItem tips\20251101_*\ -Recurse -File | 
       Select-Object Directory, Name, Length | 
       Format-Table -AutoSize
   ```
```

---

## 📊 Expected Results After Testing:

```
tips/20251101_HHMMSS/
├─ uploads/
│  └─ tips.csv
├─ reports/
│  ├─ 20251101_xxx_analyze_dataset_tool.md    ✅
│  ├─ 20251101_xxx_describe_tool_guard.md     ✅
│  ├─ 20251101_xxx_plot_tool.md               ✅
│  └─ 20251101_xxx_train_classifier.md        ✅
├─ results/
│  ├─ analyze_dataset_tool_output.json        ✅
│  ├─ describe_tool_guard_output.json         ✅
│  ├─ plot_tool_output.json                   ✅
│  └─ train_classifier_output.json            ✅
├─ plots/
│  ├─ correlation_plot.png                    ✅
│  ├─ distribution_plot.png                   ✅
│  └─ scatter_matrix.png                      ✅
└─ models/
   └─ classifier_model.pkl                    ✅
```

---

## 🚀 Quick Verification Commands:

```powershell
# After restart and testing:
cd C:\harfile\data_science_agent\data_science\.uploaded\_workspaces

# Count workspace folders (should be 1-2 max after restart)
(Get-ChildItem -Directory | Measure-Object).Count

# Find your active workspace
Get-ChildItem -Directory -Recurse -Filter "202*" | 
    Where-Object { $_.Name -match '^\d{8}_\d{6}$' } | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1

# List all files in active workspace
$latest = Get-ChildItem -Directory -Recurse -Filter "202*" | 
    Where-Object { $_.Name -match '^\d{8}_\d{6}$' } | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1
Get-ChildItem $latest.FullName -Recurse -File | 
    Select-Object @{Name="Folder";Expression={$_.Directory.Name}}, Name, 
                  @{Name="Size";Expression={"{0:N2} KB" -f ($_.Length/1KB)}} | 
    Format-Table -AutoSize
```

---

## ⚠️ If Still No Files After Restart:

1. **Check logs immediately:**
   ```powershell
   Get-Content logs\agent.log | Select-String "FILESYSTEM SAVE SUCCESS" -Context 2
   Get-Content logs\agent.log | Select-String "FALLBACK SUCCESS" -Context 2
   ```

2. **Verify workspace_root is set:**
   ```
   Look for log lines like:
   [ARTIFACT] workspace_root = C:\...\tips\20251101_HHMMSS
   ```

3. **Check for errors:**
   ```powershell
   Get-Content logs\agent.log | Select-String "ERROR|FAILED|Exception" | Select-Object -Last 20
   ```

---

## 🎯 Bottom Line:

**RESTART FIRST**, then:
1. ✅ Upload ONE dataset
2. ✅ Run ONE tool at a time
3. ✅ Wait for each to complete
4. ✅ Verify files created after each tool

**Files WILL be created** - the system is working, just needs proper restart and usage!

