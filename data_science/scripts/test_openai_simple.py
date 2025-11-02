"""Simple test to verify OpenAI configuration works."""
import os

# Set API key for testing (you'll replace this with your real key)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-test-key")

print("Testing OpenAI LiteLlm configuration...")
print("=" * 50)

try:
    from google.adk.models.lite_llm import LiteLlm
    print("OK: LiteLlm imported successfully")
    
    # Test creating a LiteLlm instance
    model = LiteLlm(model="gpt-4o-mini")
    print(f"OK: LiteLlm instance created")
    print(f"    Model: {model.model}")
    
    # Now test loading the agent
    from data_science.agent import root_agent
    print("OK: Agent loaded successfully")
    print(f"    Agent name: {root_agent.name}")
    print(f"    Model type: {type(root_agent.model).__name__}")
    if hasattr(root_agent.model, 'model'):
        print(f"    Model name: {root_agent.model.model}")
    print(f"    Number of tools: {len(root_agent.tools)}")
    
    print("\n" + "=" * 50)
    print("SUCCESS: OpenAI configuration is correct!")
    print("\nNext steps:")
    print("1. Get your OpenAI API key from: https://platform.openai.com/api-keys")
    print("2. Set it: $env:OPENAI_API_KEY='your-key-here'")
    print("3. Run: .\\start_with_openai.ps1")
    
except ImportError as e:
    print(f"ERROR: Import failed - {e}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

