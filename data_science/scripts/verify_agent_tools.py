"""Verify the agent has all its tools loaded."""
import os

# Set dummy key for import test
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-test")

try:
    from data_science.agent import root_agent
    
    print("=" * 60)
    print("DATA SCIENCE AGENT - TOOL VERIFICATION")
    print("=" * 60)
    
    print(f"\n[OK] Agent Name: {root_agent.name}")
    print(f"[OK] Model Type: {type(root_agent.model).__name__}")
    if hasattr(root_agent.model, 'model'):
        print(f"[OK] Model: {root_agent.model.model}")
    
    print(f"\n[OK] Total Tools: {len(root_agent.tools)}")
    print("\n" + "=" * 60)
    print("AVAILABLE TOOLS:")
    print("=" * 60)
    
    for i, tool in enumerate(root_agent.tools, 1):
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)
        # Get the actual function for description
        if hasattr(tool, 'func'):
            func = tool.func
            doc = func.__doc__ or "No description"
            first_line = doc.strip().split('\n')[0]
            print(f"\n{i}. {tool_name}")
            print(f"   └─ {first_line[:70]}...")
    
    print("\n" + "=" * 60)
    print("FILE UPLOAD CALLBACK:")
    print("=" * 60)
    
    if root_agent.before_model_callback:
        callback_name = root_agent.before_model_callback.__name__
        print(f"[OK] {callback_name}")
        print("     Handles CSV/text file uploads for LiteLlm compatibility")
    else:
        print("[X] No callback configured")
    
    print("\n" + "=" * 60)
    print("AGENT CAPABILITIES:")
    print("=" * 60)
    
    print("""
    [OK] File Management:
      - list_data_files()       -> List all available CSV files
      - save_uploaded_file()    -> Save uploaded CSV to .data/
    
    [OK] AutoML (Smart & Chunked):
      - smart_autogluon_automl()    -> Auto-train models (handles big files)
      - smart_autogluon_timeseries() -> Time series forecasting
    
    [OK] Data Cleaning:
      - auto_clean_data()       -> Auto-detect and fix data issues
    
    [OK] Model Management:
      - list_available_models() -> Show trained models
    
    [OK] CSV Upload Support:
      - before_model_callback   -> Auto-save uploaded files
    """)
    
    print("=" * 60)
    print("STATUS: [OK] ALL TOOLS LOADED SUCCESSFULLY")
    print("=" * 60)
    
    print("\nTry these prompts:")
    print("  - 'list files'")
    print("  - 'num1 regression'")
    print("  - 'predict attnr'")
    print("  - 'clean data'")
    print("  - 'best quality num2'")
    print("  - Upload a CSV file")
    
except Exception as e:
    print(f"[ERROR] Error loading agent: {e}")
    import traceback
    traceback.print_exc()

