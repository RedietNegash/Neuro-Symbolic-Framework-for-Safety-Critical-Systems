# llm_client.py
import os
import time
import ast
import random
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiLLMClient:
    def __init__(self, api_key: str = None, model: str = "models/gemini-1.5-flash", error_injection_rate: float = 0.0):
        load_dotenv()
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")
        self.error_injection_rate = error_injection_rate 
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not found")
                
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            raise
    
    def generate_code(self, prompt: str, specification_id: str = "", is_refinement: bool = False, max_retries: int = 3) -> str:
        if not is_refinement and random.random() < self.error_injection_rate:
            print("Injecting common LLM error pattern")
            return self._inject_common_error(specification_id, prompt)
        
        for attempt in range(max_retries):
            try:
                print(f"Calling Gemini API (attempt {attempt + 1})")
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.3 if not is_refinement else 0.1, 
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
                    return self._fallback_code_generation(prompt, specification_id)
                time.sleep(2)
    
    def _inject_common_error(self, specification_id: str, prompt: str) -> str:
        """Inject common LLM logical errors that we want to catch"""
        common_errors = {
            "drone_altitude_inclusive": [
                '''def check_altitude(altitude):
    # Common LLM error: using exclusive bounds
    if altitude > 40 and altitude < 60:
        return True
    else:
        return False''',
                '''def check_altitude(altitude):
    # Common LLM error: off-by-one
    if altitude >= 39 and altitude <= 60:
        return True
    else:
        return False'''
            ],
            "drone_altitude_exclusive": [
                '''def check_altitude(altitude):
    # Common LLM error: using inclusive bounds
    if altitude >= 40 and altitude <= 60:
        return True
    else:
        return False'''
            ],
            "robotic_grasp_safety": [
                '''def can_grasp(is_holding, action):
    # Common LLM error: missing action check
    return not is_holding''',
                '''def can_grasp(is_holding, action):
    # Common LLM error: incorrect logic
    if action == "Grasp":
        return True  # Wrong! Should return not is_holding
    return False'''
            ],
            "speed_obstacle_conditional": [
                '''def check_speed(speed, distance):
    # Common LLM error: reversed logic
    if speed > 10:
        return distance >= 20  # Wrong! Should be implies relation
    return True''',
                '''def check_speed(speed, distance):
    # Common LLM error: incorrect threshold
    if distance < 25:  # Wrong threshold
        return speed <= 10
    return True'''
            ]
        }
        
        if specification_id in common_errors:
            error_options = common_errors[specification_id]
            return random.choice(error_options)
        else:
            return self._fallback_code_generation(prompt, specification_id)
    
    def _fallback_code_generation(self, prompt: str, specification_id: str = "") -> str:
        print("Using fallback code generation")
        
        fallback_code = {
            "drone_altitude_inclusive": '''def check_altitude(altitude):
    if altitude >= 40 and altitude <= 60:
        return True
    else:
        return False''',
            
            "drone_altitude_exclusive": '''def check_altitude(altitude):
    if altitude > 40 and altitude < 60:
        return True
    else:
        return False''',
            
            "robotic_grasp_safety": '''def can_grasp(is_holding, action):
    if action == "Grasp":
        return not is_holding
    return True''',
            
            "speed_obstacle_conditional": '''def check_speed(speed, distance):
    if distance < 20:
        return speed <= 10
    return True''',
            
            "battery_emergency": '''def check_battery(voltage):
    if voltage < 11.1:
        return True
    return False'''
        }
        
        if specification_id in fallback_code:
            return fallback_code[specification_id]
        else:
            return '''def safety_function(input_value):
    return True'''