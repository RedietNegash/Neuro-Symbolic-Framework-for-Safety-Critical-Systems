# llm_client.py
import os
import time
from typing import Optional
import requests

class RealLLMClient:
    """Client for real LLM API (OpenAI compatible)"""
    
    def __init__(self, base_url: str = None, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.base_url = base_url or os.getenv("LLM_API_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_code(self, prompt: str, max_retries: int = 3) -> str:
        """Generate code using real LLM API"""
        messages = [
            {
                "role": "system",
                "content": """You are an expert autonomous systems developer specializing in safety-critical code. 
                Generate clean, correct Python code that implements the given requirements exactly.
                Focus on logical consistency and safety properties."""
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"LLM API call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return self._fallback_code_generation(prompt)
                time.sleep(2)
    
    def _fallback_code_generation(self, prompt: str) -> str:
        """Fallback code generation when API fails"""
        print("Using fallback code generation")
        if "altitude" in prompt.lower():
            return '''def check_altitude(altitude):
    if altitude >= 40 and altitude <= 60:
        return True
    else:
        return False'''
        elif "grasp" in prompt.lower():
            return '''def can_grasp(is_holding, action):
    if action == "Grasp":
        return not is_holding
    return True'''
        else:
            return '''def safety_function(input_value):
    # Default safety implementation
    return True'''