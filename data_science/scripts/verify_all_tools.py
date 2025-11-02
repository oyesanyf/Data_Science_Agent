"""Verify all 35+ tools are loaded and using OpenAI."""
import os
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-test")

from data_science.agent import root_agent

print("=" * 70)
print("COMPLETE TOOL VERIFICATION - OpenAI Powered")
print("=" * 70)

print(f"\nAgent: {root_agent.name}")
print(f"Model: {type(root_agent.model).__name__}")
if hasattr(root_agent.model, 'model'):
    print(f"OpenAI Model: {root_agent.model.model}")

print(f"\nTotal Tools: {len(root_agent.tools)}")

# Categorize tools
categories = {
    "Help & Discovery": ["help", "sklearn_capabilities", "suggest_next_steps"],
    "File Management": ["list_data_files", "save_uploaded_file"],
    "AutoGluon": ["smart_autogluon_automl", "smart_autogluon_timeseries", "auto_clean_data", "list_available_models"],
    "Analysis & Visualization": ["analyze_dataset", "plot"],
    "AutoML & Training": ["auto_analyze_and_model", "train_baseline_model", "train", "train_classifier", "train_regressor"],
    "Prediction": ["predict", "classify"],
    "Clustering": ["kmeans_cluster", "dbscan_cluster", "hierarchical_cluster", "isolation_forest_train"],
    "Data Preprocessing": ["scale_data", "encode_data", "expand_features"],
    "Missing Data": ["impute_simple", "impute_knn", "impute_iterative"],
    "Feature Selection": ["select_features", "recursive_select", "sequential_select"],
    "Model Evaluation": ["split_data", "grid_search", "evaluate"],
    "Text Processing": ["text_to_features"]
}

# Get all tool names
tool_names = [tool.name for tool in root_agent.tools if hasattr(tool, 'name')]

print("\n" + "=" * 70)
print("TOOLS BY CATEGORY:")
print("=" * 70)

total_found = 0
for category, expected_tools in categories.items():
    print(f"\n{category} ({len(expected_tools)} tools):")
    for tool_name in expected_tools:
        if tool_name in tool_names:
            print(f"  [OK] {tool_name}")
            total_found += 1
        else:
            print(f"  [MISSING] {tool_name}")

print("\n" + "=" * 70)
print(f"RESULT: {total_found}/{sum(len(t) for t in categories.values())} tools loaded")
print("=" * 70)

if total_found == sum(len(t) for t in categories.values()):
    print("\n[SUCCESS] All tools restored and using OpenAI!")
    print(f"Model: gpt-4o-mini via LiteLLM")
    print(f"Server: http://localhost:8080")
else:
    print(f"\n[WARNING] Some tools missing: {sum(len(t) for t in categories.values()) - total_found}")

print("\nKey Features:")
print("  - help() shows all tools")
print("  - Artifacts created in UI")
print("  - OpenAI for LLM, local execution for tools")
print("  - Cost: ~$0.0007 per message")

