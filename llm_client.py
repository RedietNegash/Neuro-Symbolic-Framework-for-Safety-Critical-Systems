# llm_client.py
import os
import time
from typing import Optional
import google.generativeai as genai  # UNCOMMENTED
from dotenv import load_dotenv

class GeminiLLMClient:
    """Client for Google Gemini LLM API"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"): 
        load_dotenv()
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client"""
        try:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
                
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            print("Trying to list available models...")
            self._list_available_models()
            raise
    
    def _list_available_models(self):
        """List available models for debugging"""
        try:
            models = genai.list_models()
            print("Available models:")
            for model in models:
                print(f"  - {model.name}")
        except Exception as e:
            print(f" Could not list models: {e}")
    
    def generate_code(self, prompt: str, max_retries: int = 3) -> str:
        """Generate code using Google Gemini API"""
        
        for attempt in range(max_retries):
            try:
                print(f"Calling Gemini API (attempt {attempt + 1})...")
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.1,
                        'max_output_tokens': 1000,
                    }
                )
                
                if response.text:
                    print("Gemini response received")
                    return response.text.strip()
                else:
                    raise ValueError("Empty response from Gemini")
                    
            except Exception as e:
                print(f"Gemini API call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    print("🔄 Using fallback code generation")
                    return self._fallback_code_generation(prompt)
                time.sleep(2)
    
    def _fallback_code_generation(self, prompt: str) -> str:
        """Fallback code generation when API fails"""
        print("Using fallback code generation")
        
        if "altitude" in prompt.lower():
            return '''def check_altitude(altitude):
        return altitude >= 40 and altitude <= 60'''
        
        elif "execution_time" in prompt.lower():
            return '''def check_execution_time(execution_time):
        return execution_time <= 10'''
        
        elif "imu" in prompt.lower() or "fault" in prompt.lower():
            return '''def check_imu(imu1_failed, active_imu):
        return not imu1_failed or active_imu == 2'''
        
        elif "gps" in prompt.lower() or "velocity" in prompt.lower():
            return '''def check_velocity(gps_vel, imu_vel):
        return abs(gps_vel - imu_vel) <= 2.0'''
        
        elif "signature" in prompt.lower():
            return '''def check_signature(is_signature_valid, action):
        return is_signature_valid or action == 'None' '''
        
        elif "battery" in prompt.lower():
            return '''def check_battery(battery_level, command):
        return battery_level >= 15 or command == 'RTH' '''
        
        elif "heap" in prompt.lower() or "memory" in prompt.lower():
            return '''def check_heap_usage(heap_usage):
        return heap_usage <= 80'''
        
        else:
            return '''def safety_check(value):
        return True'''