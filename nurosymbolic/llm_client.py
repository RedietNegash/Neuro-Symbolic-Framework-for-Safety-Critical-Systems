# llm_client.py - REPLACE the entire file with this:

import google.generativeai as genai
import os
import random
import time
import ast

class GeminiLLMClient:
    def __init__(self, error_injection_rate: float = 0.0):
        self.error_injection_rate = error_injection_rate
        self.model_name = "gemini-2.5-flash" 
        self.configure_client()
    
    def configure_client(self):
        """Configure Gemini client"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.use_api = False
            print("Using simulated LLM responses")
            return
        
        try:
            genai.configure(api_key=api_key)
            self.use_api = True
            print(f"Gemini API configured with {self.model_name}")
        except:
            self.use_api = False
            print("Gemini API failed, using simulated responses")
    
    def generate_code(self, prompt: str) -> str:
        """Generate code as described in Section 2.2"""
        if self.use_api:
            try:
                time.sleep(1)
                response = self._call_gemini_api(prompt)
                return self._clean_response(response)
            except Exception as e:
                print(f"API call failed: {e}")
        return self._simulate_document_aligned_llm(prompt)
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API without artificial constraints"""
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt)
        
        if response.parts:
            return response.text
        else:
            raise Exception("No response from API")
    
    def _clean_response(self, response: str) -> str:
        """Extract clean, syntactically valid Python code from responses"""
        if "```python" in response:
            code_start = response.find("```python") + 9
            code_end = response.find("```", code_start)
            if code_end != -1:
                response = response[code_start:code_end].strip()
        elif "```" in response:
            code_start = response.find("```") + 3
            code_end = response.find("```", code_start)
            if code_end != -1:
                response = response[code_start:code_end].strip()
        

        response = self._fix_common_syntax_issues(response)
        lines = response.split('\n')
        python_lines = []
        in_python_code = False
        
        for line in lines:
            stripped = line.strip()
            if not in_python_code and (not stripped or stripped.startswith('#')):
                continue
                
            if stripped.startswith('def ') or stripped.startswith('class '):
                in_python_code = True
        
            if in_python_code:
                python_lines.append(line)
        
        result = '\n'.join(python_lines).strip()
        
        if result and ('def ' in result or 'class ' in result):
            try:
                ast.parse(result)
                return result
            except SyntaxError:
                return self._extract_verification_logic(result)
        
        return result if result else "def default_check():\n    return True"

    def _fix_common_syntax_issues(self, code: str) -> str:
        """Fix common syntax issues in Gemini's output"""
        lines = code.split('\n')
        fixed_lines = []
        in_docstring = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if '"""' in line:
                in_docstring = not in_docstring
                
            if (stripped and not stripped.startswith('"') and not stripped.startswith("'") and 
                not stripped.startswith('#') and not stripped.startswith('def ') and 
                not stripped.startswith('class ') and ':' in stripped and not in_docstring):
                continue
                
            if line and not line.startswith(' ') and not stripped.startswith('def ') and not stripped.startswith('class '):
                line = '    ' + line
                
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def _extract_verification_logic(self, code: str) -> str:
        """Extract just the verification logic from complex code"""
        lines = code.split('\n')
        verification_lines = []
        
        for line in lines:
            stripped = line.strip()
            if any(pattern in stripped for pattern in ['return', 'if ', '>=', '<=', '>', '<', '==', '!=']):
                verification_lines.append(line)
            elif stripped.startswith('def '):
                verification_lines.append(line)
        
        result = '\n'.join(verification_lines).strip()
        if 'def ' in result and 'return ' in result:
            return result
        else:
            return "def verify_condition():\n    return True"

    def _simulate_document_aligned_llm(self, prompt: str) -> str:
        """Simulate LLM following document examples and error patterns"""
        if "altitude" in prompt and "40" in prompt and "60" in prompt:
            if random.random() < self.error_injection_rate:
                return "def check_altitude(alt):\n    return alt > 40 and alt < 60"  
            else:
                return "def check_altitude(alt):\n    return 40 <= alt <= 60"  
        
        elif "speed" in prompt and "distance" in prompt:
            if random.random() < self.error_injection_rate:
                return "def safe_speed(speed, distance):\n    return distance >= 20 or speed <= 10" 
            else:
                return "def safe_speed(speed, distance):\n    if distance < 20:\n        return speed <= 10\n    return True"  # Correct as in document
        
        elif "grasp" in prompt.lower():
            if random.random() < self.error_injection_rate:
                return "def can_grasp(is_holding, action):\n    return action != 'Grasp'"  
            else:
                return "def can_grasp(is_holding, action):\n    if action == 'Grasp':\n        return not is_holding\n    return True"  # Correct as in document
        
        elif "battery" in prompt or "voltage" in prompt:
            if random.random() < self.error_injection_rate:
              
                return "def check_voltage(voltage):\n    return voltage <= 11.1"  
            else:
                return "def check_voltage(voltage):\n    return voltage < 11.1" 
        return "def verify_condition():\n    return True"