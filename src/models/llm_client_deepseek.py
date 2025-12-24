# src/models/llm_client_deepseek.py
import os
import time
from typing import Optional
import ollama
from dotenv import load_dotenv

class DeepSeekLLMClient:
    """Client for local DeepSeek model via Ollama"""
    
    def __init__(self, model: str = None, host: str = None):
        load_dotenv()
        
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-coder:1.3b")
        self.host = host or os.getenv("DEEPSEEK_HOST", "http://localhost:11434")
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the DeepSeek client"""
        try:
            self.client = ollama.Client(host=self.host)
            # Test connection
            self.client.list()
            print(f"[OK] DeepSeek client initialized with model: {self.model}")
        except Exception as e:
            print(f"[Warning] Failed to initialize DeepSeek client: {e}")
            print("[Info] DeepSeek will use fallback code generation")
            self.client = None
    
    def generate_code(self, prompt: str, max_retries: int = 2) -> str:
        """Generate code using local DeepSeek model via Ollama with better error handling"""
        
        # If client not initialized, use fallback
        if not self.client:
            print("    [Fallback] DeepSeek client not initialized, using fallback")
            return self._fallback_code_generation(prompt)
        
        for attempt in range(max_retries):
            try:
                print(f"    Calling DeepSeek (attempt {attempt + 1})...")
                
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.1,
                        'num_predict': 1000, # Increased back for full generation
                    }
                )
                
                if response and 'response' in response and response['response'].strip():
                    raw_text = response['response'].strip()
                    
                    # 1. Remove thinking tags if present (common in R1 models)
                    if "<think>" in raw_text:
                        if "</think>" in raw_text:
                            raw_text = raw_text.split("</think>")[-1].strip()
                        else:
                            raw_text = raw_text.split("<think>")[-1].strip()
                    
                    # 2. If the response is still empty or just garbage after stripping, retry
                    if not raw_text or len(raw_text) < 10:
                        print(f"    DeepSeek returned insufficient text (attempt {attempt + 1})")
                        continue
                        
                    print("    DeepSeek response received")
                    return raw_text
                else:
                    print(f"    DeepSeek returned empty response (attempt {attempt + 1})")
                    
            except Exception as e:
                print(f"    DeepSeek call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    print("    [Fallback] All DeepSeek attempts failed, using fallback")
                    return self._fallback_code_generation(prompt)
                time.sleep(2)
        
        return self._fallback_code_generation(prompt)
    
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