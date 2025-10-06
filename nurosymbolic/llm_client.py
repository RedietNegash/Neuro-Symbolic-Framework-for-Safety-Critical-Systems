# llm_client.py
import google.generativeai as genai
import os
import random
from typing import Optional

class GeminiLLMClient:
    def __init__(self, error_injection_rate: float = 0.0):
        self.error_injection_rate = error_injection_rate
        self.configure_client()
    
    def configure_client(self):
        """Configure the Gemini client"""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "your-gemini-api-key-here":
            genai.configure(api_key=api_key)
        else:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    def generate_code(self, prompt: str) -> str:
        """Generate code with optional error injection for testing"""
        try:
            # For demonstration, we'll simulate LLM responses
            # In a real implementation, you'd call the actual Gemini API
            return self._simulate_llm_response(prompt)
        except Exception as e:
            return f"# Error generating code: {str(e)}\n# Simulated code for testing\ndef simulated_function():\n    return True"
    
    def _simulate_llm_response(self, prompt: str) -> str:
        """Simulate LLM responses with realistic error patterns"""
        
        # Simulate different response patterns based on prompt content
        if "altitude" in prompt and ">=" in prompt:
            if random.random() < self.error_injection_rate:
                # Inject boundary error
                return "def check_altitude(altitude):\n    return altitude > 40 and altitude < 60"  # Exclusive instead of inclusive
            else:
                return "def check_altitude(altitude):\n    return altitude >= 40 and altitude <= 60"
        
        elif "speed" in prompt and "distance" in prompt:
            if random.random() < self.error_injection_rate:
                # Inject conditional error
                return "def check_speed(speed, distance):\n    if distance <= 20:\n        return speed < 10"  # Wrong operator
            else:
                return "def check_speed(speed, distance):\n    if distance < 20:\n        return speed <= 10\n    return True"
        
        elif "grasp" in prompt.lower() or "holding" in prompt:
            if random.random() < self.error_injection_rate:
                # Inject logic error
                return "def can_grasp(is_holding, action):\n    if action == 'Grasp':\n        return is_holding"  # Wrong logic
            else:
                return "def can_grasp(is_holding, action):\n    if action == 'Grasp':\n        return not is_holding\n    return True"
        
        else:
            # Default response
            return "def implemented_function():\n    # Default implementation\n    return True"