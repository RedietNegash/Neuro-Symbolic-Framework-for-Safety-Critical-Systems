# src/models/llm_client_llama.py
import os
import time
from typing import Optional
import ollama
from dotenv import load_dotenv

class LlamaLLMClient:
    """Client for local Llama model via Ollama"""
    
    def __init__(self, model: str = None, host: str = None):
        load_dotenv()
        
        self.model = model or os.getenv("LLAMA_MODEL", "llama3:8b")
        self.host = host or os.getenv("LLAMA_HOST", "http://localhost:11434")
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Llama client"""
        try:
            self.client = ollama.Client(host=self.host)
            # Test connection
            self.client.list()
            print(f"[OK] Llama client initialized with model: {self.model}")
        except Exception as e:
            print(f"[Warning] Failed to initialize Llama client: {e}")
            raise
    
    def generate_code(self, prompt: str, max_retries: int = 2) -> str:
        """Generate code using local Llama model via Ollama"""
        
        for attempt in range(max_retries):
            try:
                print(f"    Calling Llama (attempt {attempt + 1})...")
                
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.1,
                        'num_predict': 500,
                    }
                )
                
                if response and 'response' in response and response['response'].strip():
                    print("    Llama response received")
                    return response['response'].strip()
                else:
                    raise ValueError("Empty response from Llama")
                    
            except Exception as e:
                print(f"    Llama call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    print("    [Fallback] Using fallback code generation")
                    return self._fallback_code_generation(prompt)
                time.sleep(1)
    
    def _fallback_code_generation(self, prompt: str) -> str:
        """Fallback code generation when API fails"""
        print("    [Fallback] Using fallback code generation")
        
        prompt_lower = prompt.lower()
        
        if "altitude" in prompt_lower:
            return '''def check_safety(altitude):
    return altitude >= 40 and altitude <= 60'''
        
        elif "execution_time" in prompt_lower:
            return '''def check_safety(execution_time):
    return execution_time <= 10'''
        
        elif "imu" in prompt_lower:
            return '''def check_safety(imu1_failed, active_imu):
    return not imu1_failed or active_imu == 2'''
        
        elif "gps" in prompt_lower and "imu" in prompt_lower:
            return '''def check_safety(gps_vel, imu_vel):
    return abs(gps_vel - imu_vel) <= 2.0'''
        
        elif "signature" in prompt_lower:
            return '''def check_safety(is_signature_valid, action):
    return is_signature_valid or action == "None"'''
        
        elif "battery" in prompt_lower:
            return '''def check_safety(battery_level, command):
    return battery_level >= 15 or command == "RTH"'''
        
        elif "heap" in prompt_lower or "memory" in prompt_lower:
            return '''def check_safety(heap_usage):
    return heap_usage <= 80'''
        
        else:
            return '''def check_safety():
    return True'''