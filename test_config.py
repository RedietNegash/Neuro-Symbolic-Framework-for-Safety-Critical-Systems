from src.core import config
from src.models.llm_client_deepseek import DeepSeekLLMClient

def test_config():
    print(f"DeepSeek Model in Config: {config.DEEPSEEK_MODEL}")
    
    try:
        client = DeepSeekLLMClient()
        print(f"DeepSeek Client Model: {client.model}")
        print("DeepSeek client initialized successfully.")
    except Exception as e:
        print(f"DeepSeek client initialization failed: {e}")

if __name__ == "__main__":
    test_config()
