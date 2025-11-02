"""
Verify the running server has the new artifact routing code.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force fresh import
for mod in list(sys.modules.keys()):
    if 'data_science' in mod:
        del sys.modules[mod]

from data_science import agent as agent_module
import inspect

print("\n" + "="*75)
print(" VERIFYING SERVER CODE")
print("="*75)

# Check 1: SafeFunctionTool structure
print("\n1⃣ Checking SafeFunctionTool...")
if hasattr(agent_module, 'SafeFunctionTool'):
    source = inspect.getsource(agent_module.SafeFunctionTool)
    
    # Should NOT have whitelist check anymore
    if "_ARTIFACT_GENERATING_TOOLS" in source:
        print("   [X] OLD CODE: Still checking whitelist")
        print("   → Server is using OLD cached code!")
    else:
        print("   [OK] NEW CODE: No whitelist check")
        
    # Should have artifact routing wrapper call
    if "make_artifact_routing_wrapper" in source:
        print("   [OK] NEW CODE: Calls make_artifact_routing_wrapper")
    else:
        print("   [X] OLD CODE: Doesn't call wrapper")
        
    # Should apply to ALL tools (no if statement checking func name)
    if "if func.__name__ in" in source:
        print("   [X] OLD CODE: Only wraps specific tools")
    else:
        print("   [OK] NEW CODE: Wraps ALL tools")
else:
    print("   [X] SafeFunctionTool not found!")

# Check 2: Workspace creation for detected names
print("\n2⃣ Checking workspace creation logic...")
full_source = inspect.getsource(agent_module)
if 'if detected_name != "uploaded":' in full_source:
    # Check if workspace is initialized after detection
    lines = full_source.split('\n')
    for i, line in enumerate(lines):
        if 'if detected_name != "uploaded":' in line:
            # Check next 15 lines for ensure_workspace
            next_lines = '\n'.join(lines[i:i+15])
            if 'ensure_workspace(callback_context.state' in next_lines:
                print("   [OK] NEW CODE: Workspace created after content detection")
            else:
                print("   [X] OLD CODE: Workspace NOT created after content detection")
            break
else:
    print("   [WARNING]  Could not find content detection code")

# Check 3: plot() returns full paths
print("\n3⃣ Checking plot() function...")
try:
    from data_science import ds_tools
    plot_source = inspect.getsource(ds_tools.plot)
    
    if "artifacts.append(plot_path)" in plot_source:
        print("   [OK] NEW CODE: plot() appends full paths")
    elif "artifacts.append(filename)" in plot_source:
        print("   [X] OLD CODE: plot() appends filenames only")
    else:
        print("   [WARNING]  Could not find artifacts.append statement")
        
    if '"plot_paths": artifacts' in plot_source:
        print("   [OK] NEW CODE: plot() includes plot_paths key")
    else:
        print("   [WARNING]  plot_paths key not found")
except Exception as e:
    print(f"   [X] Could not check plot(): {e}")

print("\n" + "="*75)
print(" VERDICT")
print("="*75)

issues_found = []
if "_ARTIFACT_GENERATING_TOOLS" in source:
    issues_found.append("SafeFunctionTool still uses OLD whitelist logic")
if "if func.__name__ in" in source:
    issues_found.append("SafeFunctionTool only wraps specific tools (OLD)")

if issues_found:
    print("\n[X] SERVER IS RUNNING OLD CODE!")
    print("\nIssues found:")
    for issue in issues_found:
        print(f"  • {issue}")
    print("\n SOLUTION:")
    print("  1. Stop-Process -Name python -Force")
    print("  2. Remove-Item -Recurse -Force data_science\\__pycache__")
    print("  3. .\\start_server.bat")
    print("  4. Wait for 'Application startup complete'")
else:
    print("\n[OK] SERVER HAS NEW CODE!")
    print("\nIf artifacts still aren't being copied:")
    print("  • Check that you uploaded a NEW file (new session)")
    print("  • Check that you RAN a tool (analyze_dataset or plot)")
    print("  • Check the SERVER CONSOLE (not UI) for messages")
    print("  • If still nothing, the wrapper may not be triggering")

print("\n" + "="*75 + "\n")

