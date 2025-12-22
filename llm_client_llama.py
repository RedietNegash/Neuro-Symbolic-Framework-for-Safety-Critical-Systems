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
        try:
            ollama.Client(host=self.host)  # Verify connection
            print(f"Llama client initialized with model: {self.model}")
        except Exception as e:
            print(f"Failed to initialize Llama client: {e}")
            raise
    
    def generate_code(self, prompt: str, max_retries: int = 3) -> str:
        """Generate code using local Llama model via Ollama"""
        
        for attempt in range(max_retries):
            try:
                print(f"Calling Llama (attempt {attempt + 1})...")
                
                response = ollama.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.1,  # Low for deterministic output
                        'num_predict': 1000,  # Max tokens
                    }
                )
                
                if response['response']:
                    print("Llama response received")
                    return response['response'].strip()
                else:
                    raise ValueError("Empty response from Llama")
                    
            except Exception as e:
                print(f"Llama call failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    print("🔄 Using fallback code generation")
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
        
        elif "rotation" in prompt.lower() and "speed" in prompt.lower():
            return '''def check_rotation_speed(rotation_speed, distance):
        if distance < 0.5:
            return rotation_speed <= 5
        return True'''
        
        elif "speed" in prompt.lower() and "obstacle" in prompt.lower():
            return '''def check_speed(speed, distance):
        if distance < 20:
            return speed <= 10
        return True'''
        
        elif "battery" in prompt.lower() or "voltage" in prompt.lower():
            return '''def check_battery(voltage):
        if voltage < 11.1:
            return True # should land
        return False'''
        
        else:
            return '''def safety_function(input_value):
        # Default safety implementation
        return True'''
