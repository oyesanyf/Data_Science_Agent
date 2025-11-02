# ⚠️ CRITICAL: Server Must Be COMPLETELY RESTARTED

## 🔍 The Problem

The artifact routing code **EXISTS in the files** but is **NOT LOADED in the running server**.

## Evidence

1. ✅ `plot()` creates files with full paths (fixed)
2. ✅ `_ARTIFACT_GENERATING_TOOLS` exists in agent.py (line 267)
3. ✅ `SafeFunctionTool` exists in agent.py (line 286)  
4. ❌ **But when we import the module, these don't exist!**
5. ❌ **No files are being copied to workspace**
6. ❌ **No console `📦 Artifact copied:` messages**

This means the **server process is using OLD cached modules** from memory.

## ✅ Solution: HARD RESTART

### Step 1: STOP the Server COMPLETELY

In the terminal where the server is running:
1. Press `Ctrl+C` to stop it
2. **WAIT** for it to fully exit
3. If it doesn't stop, press `Ctrl+C` again
4. **Confirm the process is dead** (no more console output)

### Step 2: Clear ALL Python Cache

```powershell
# Run this from project root
Remove-Item -Recurse -Force data_science\__pycache__
Remove-Item -Recurse -Force __pycache__
Get-ChildItem -Path . -Filter '*.pyc' -Recurse | Remove-Item -Force
```

### Step 3: Start Fresh Server

```powershell
# Use the batch file (it clears cache automatically)
.\start_server.bat
```

**OR** if you're using Python directly:

```powershell
python start_server.py
```

### Step 4: Wait for Server to Fully Start

Wait until you see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://...
```

### Step 5: Test with Fresh Upload

1. **Upload a NEW CSV file** (don't reuse old session)
2. In the UI chat, type: **"Analyze my dataset"**
3. **Watch the SERVER CONSOLE** (terminal window, NOT the UI chat)
4. You should see:
   ```
   📦 Artifact copied: yourfile_auto_hist_col1.png → plots/
   📦 Artifact copied: yourfile_auto_hist_col2.png → plots/
   ...
   ✅ Routed 8 artifact(s) to workspace: yourfile/20251017_HHMMSS/
   ```

### Step 6: Verify Files in Workspace

```powershell
dir .uploaded\_workspaces\yourfile\*\plots
```

You should see PNG files!

---

## ⚠️ Important Notes

### "Restarting" is NOT the Same as "Stopping and Starting"

- ❌ **NOT sufficient**: Hot-reload, file save, module reload
- ❌ **NOT sufficient**: Clicking "restart" in some IDEs
- ✅ **REQUIRED**: Complete process termination + new process start

### How to Confirm Server is Stopped

Before restarting, confirm the terminal shows:
```
^C (Ctrl+C pressed)
INFO:     Shutting down
INFO:     Finished server process
(back to command prompt)
```

### If Server Won't Stop

```powershell
# Find Python processes
Get-Process python

# Kill them
Stop-Process -Name python -Force
```

---

## 🧪 Quick Test After Restart

Run this to confirm the new code is loaded:

```powershell
python -c "from data_science import agent; print('Whitelist exists:' if hasattr(agent, '_ARTIFACT_GENERATING_TOOLS') else 'Whitelist MISSING'); print('SafeFunctionTool exists:' if hasattr(agent, 'SafeFunctionTool') else 'SafeFunctionTool MISSING')"
```

**Expected output AFTER restart:**
```
Whitelist exists:
SafeFunctionTool exists:
```

**If you see "MISSING"** → The server is still using old code!

---

## 🎯 Bottom Line

**You MUST completely stop the Python process and start a new one.**

Just saving files or "restarting" within an IDE won't work because Python caches imported modules in memory.

**The fix is in the code. The server just needs to load it!**

