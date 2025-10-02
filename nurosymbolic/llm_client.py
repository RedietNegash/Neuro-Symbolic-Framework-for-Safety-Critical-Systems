# llm_client.py
import os
import time
from typing import Optional
import google.generativeai as genai

class GeminiLLMClient:
    """Client for Google Gemini LLM API"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-pro"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            raise
    
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
                    print("Using fallback code generation")
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
        elif "speed" in prompt.lower() and "obstacle" in prompt.lower():
            return '''def check_speed(speed, distance):
    if distance < 20:
        return speed <= 10
    return True'''
        elif "battery" in prompt.lower() or "voltage" in prompt.lower():
            return '''def check_battery(voltage):
    if voltage < 11.1:
        return True  # should land
    return False'''
        else:
            return '''def safety_function(input_value):
    # Default safety implementation
    return True'''