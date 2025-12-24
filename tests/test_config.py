# tests/test_config.py
import sys
import os

# Add the parent directory to Python path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core import config
from src.models.llm_ensemble import LLMEnsemble

def test_config():
    """Test that configuration is loaded correctly"""
    print("Testing configuration...")
    print(f"Gemini API Key: {'✓ Set' if config.GEMINI_API_KEY else '✗ Not set'}")
    print(f"Gemini Model: {config.GEMINI_MODEL}")
    print(f"Llama Model: {config.LLAMA_MODEL}")
    print(f"DeepSeek Model: {config.DEEPSEEK_MODEL}")
    print(f"Active Approach: {config.ACTIVE_APPROACH}")
    
    # Try to initialize ensemble
    try:
        ensemble = LLMEnsemble()
        print(f"\nEnsemble initialized with {len(ensemble.clients)} models:")
        for name, client in ensemble.clients.items():
            print(f"  ✓ {name}")
        return True
    except Exception as e:
        print(f"\nError initializing ensemble: {e}")
        return False

if __name__ == "__main__":
    success = test_config()
    exit(0 if success else 1)