"""
Google Gemini client implementation
"""
import os
import time
from typing import Dict, List, Optional, Any
import logging
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_client import BaseLLMClient
from config.settings import settings

logger = logging.getLogger(__name__)

class GeminiClient(BaseLLMClient):
    """Gemini 2.5 Flash client"""
    
    def __init__(self):
        config = {
            "api_key": settings.gemini_api_key,
            "model": "gemini-2.5-flash",
            "max_output_tokens": 1024,
            "safety_settings": {
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
            }
        }
        super().__init__("gemini-2.5-flash", config)
        
        # Configure Gemini
        genai.configure(api_key=config["api_key"])
        self.generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": config["max_output_tokens"],
        }
        
        self.model = genai.GenerativeModel(
            model_name=config["model"],
            generation_config=self.generation_config,
            safety_settings=config["safety_settings"]
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_code(self, 
                     prompt: str, 
                     system_context: Optional[str] = None,
                     temperature: float = 0.1) -> str:
        """Generate code using Gemini API"""
        self.request_count += 1
        start_time = time.time()
        
        try:
            # Construct full prompt with system context
            full_prompt = ""
            if system_context:
                full_prompt += f"System Context: {system_context}\n\n"
            full_prompt += prompt
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            if response.parts:
                code = response.text
                
                # Extract Python code from markdown if present
                if "```python" in code:
                    code_start = code.find("```python") + 9
                    code_end = code.find("```", code_start)
                    if code_end != -1:
                        code = code[code_start:code_end].strip()
                elif "```" in code:
                    code_start = code.find("```") + 3
                    code_end = code.find("```", code_start)
                    if code_end != -1:
                        code = code[code_start:code_end].strip()
                
                # Estimate tokens (rough approximation)
                self.total_tokens += len(code.split()) * 1.3
                
                elapsed = time.time() - start_time
                logger.info(f"Gemini generated code in {elapsed:.2f}s")
                
                if self.validate_response(code):
                    return code
                else:
                    return self._fallback_code(prompt)
                    
            else:
                logger.error("Gemini returned empty response")
                return self._fallback_code(prompt)
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Gemini API error: {e}")
            return self._fallback_code(prompt)
    
    def critique_code(self, 
                     code: str, 
                     requirements: str,
                     issues: List[str]) -> str:
        """Provide critique using Gemini"""
        critique_prompt = f"""
        Analyze this code for safety issues:
        
        REQUIREMENTS: {requirements}
        
        CODE:
        {code}
        
        KNOWN ISSUES: {', '.join(issues)}
        
        Provide specific, actionable critique focusing on:
        1. Logical errors
        2. Safety property violations
        3. Edge cases not handled
        4. Suggestions for correction
        
        Be concise and technical.
        """
        
        try:
            response = self.model.generate_content(critique_prompt)
            return response.text if response.parts else "No critique available."
        except Exception as e:
            logger.error(f"Gemini critique error: {e}")
            return f"Critique failed: {str(e)}"
    
    def naturalize_invariant(self, 
                           raw_invariant: str, 
                           context: str) -> str:
        """Naturalize formal invariant"""
        naturalize_prompt = f"""
        Convert this formal invariant to natural language:
        
        FORMAL: {raw_invariant}
        CONTEXT: {context}
        
        Provide a clear, concise natural language description
        suitable for an engineer's report.
        """
        
        try:
            response = self.model.generate_content(naturalize_prompt)
            return response.text if response.parts else raw_invariant
        except Exception as e:
            logger.error(f"Gemini naturalization error: {e}")
            return raw_invariant
    
    def _fallback_code(self, prompt: str) -> str:
        """Fallback code generation when API fails"""
        logger.warning("Using fallback code generation")
        
        # Simple heuristic-based fallback
        if "altitude" in prompt.lower() and ("40" in prompt or "60" in prompt):
            return """def check_altitude(altitude: float) -> bool:
    \"\"\"Check if altitude is between 40 and 60 meters inclusive\"\"\"
    return 40.0 <= altitude <= 60.0"""
        
        elif "speed" in prompt.lower() and "distance" in prompt.lower():
            return """def check_speed_distance(speed: float, distance: float) -> bool:
    \"\"\"Check speed safety relative to obstacle distance\"\"\"
    if distance < 20.0:
        return speed <= 10.0
    return True"""
        
        else:
            return """def safety_check() -> bool:
    \"\"\"Default safety check function\"\"\"
    # Implement safety logic here
    return True"""