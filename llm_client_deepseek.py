import os
import time
from typing import Optional
import ollama
from dotenv import load_dotenv

class DeepSeekLLMClient:
    """Client for local DeepSeek-Coder model via Ollama"""
    
    def __init__(self, model: str = None, host: str = None):
        load_dotenv()
        
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-coder:1.3b")
        self.host = host or os.getenv("DEEPSEEK_HOST", "http://localhost:11434")
        try:
            ollama.Client(host=self.host)
            print(f"DeepSeek client initialized with model: {self.model}")
        except Exception as e:
            print(f"Failed to initialize DeepSeek client: {e}")
            raise
    
    def generate_code(self, prompt: str, max_retries: int = 3) -> str:
        """Generate code using local DeepSeek model via Ollama"""
        
        for attempt in range(max_retries):
            try:
                print(f"Calling DeepSeek (attempt {attempt + 1})...")
                
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.1,
                        'num_predict': 1000,
                    }
                )
                
                if response['response']:
                    print("DeepSeek response received")
                    return response['response'].strip()
                else:
                    raise ValueError("Empty response from DeepSeek")
                    
            except Exception as e:
                print(f"DeepSeek call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return "# Error: DeepSeek call failed"
                time.sleep(2)
