import asyncio
from typing import List, Dict, Any, Optional, Tuple
from llm_client import GeminiLLMClient  # ADDED
from llm_client_llama import LlamaLLMClient
from llm_client_deepseek import DeepSeekLLMClient
import ast
import re

class LLMEnsemble:
    """Orchestrates an ensemble of LLMs for verified code synthesis with tracking"""
    
    def __init__(self, include_gemini: bool = True):
        self.clients = {
            "llama": LlamaLLMClient(),
            "deepseek": DeepSeekLLMClient()
        }
        
        # Add Gemini if available
        if include_gemini:
            try:
                self.clients["gemini"] = GeminiLLMClient()
                print("✅ Gemini added to ensemble")
            except Exception as e:
                print(f"⚠️ Could not add Gemini to ensemble: {e}")
                print("Continuing with Llama and DeepSeek only")
        
        self.logs = []
        self.last_selected_model = None
        self.model_selection_history = []
        print(f"Ensemble initialized with {len(self.clients)} models: {', '.join(self.clients.keys())}")
    
    async def generate_ensemble(self, prompt: str) -> Dict[str, str]:
        """Run all LLMs in parallel and return their outputs"""
        async def _call_client(name, client):
            try:
                print(f"    [{name.upper()}] generating code...")
                loop = asyncio.get_event_loop()
                code = await loop.run_in_executor(None, client.generate_code, prompt)
                return name, code
            except Exception as e:
                print(f"    [{name.upper()}] error: {e}")
                return name, None

        tasks = [_call_client(name, client) for name, client in self.clients.items()]
        responses = await asyncio.gather(*tasks)
        return dict(responses)

    def arbitrate(self, candidates: Dict[str, str]) -> Optional[str]:
        """Select the best candidate based on simplicity with tracking"""
        valid_candidates = {}
        candidate_scores = {}
        
        print("    Evaluating candidates...")
        
        for name, code in candidates.items():
            if not code:
                print(f"    [{name.upper()}] no code generated")
                continue
            
            clean_code = self._extract_python_code(code)
            if not clean_code:
                print(f"    [{name.upper()}] no Python code found in response")
                continue
            
            # Score based on multiple criteria
            score = self._calculate_code_score(clean_code, name)
            candidate_scores[name] = score
            
            # Check syntax with better error handling
            syntax_valid, error_msg = self._check_syntax_with_detail(clean_code)
            if syntax_valid:
                valid_candidates[name] = clean_code
                print(f"    [{name.upper()}] valid syntax, score: {score:.1f}")
            else:
                print(f"    [{name.upper()}] syntax error: {error_msg}")
                continue
        
        if not valid_candidates:
            print("    No valid candidates found")
            return None
        
        # Select best candidate
        best_name = min(candidate_scores.items(), key=lambda x: x[1])[0]
        best_code = valid_candidates[best_name]
        
        self.last_selected_model = best_name
        self.model_selection_history.append({
            "selected_model": best_name,
            "all_scores": candidate_scores,
            "candidates": list(valid_candidates.keys()),
            "timestamp": asyncio.get_event_loop().time()
        })
        
        print(f"    Selected {best_name.upper()} with score {candidate_scores[best_name]:.1f}")
        return best_code
    
    def _calculate_code_score(self, code: str, model_name: str) -> float:
        """Calculate score for code quality (lower is better)"""
        score = len(code) * 0.01  # Penalize length less harshly
        
        # Penalize complex constructs
        if 'if ' in code.lower() or 'elif ' in code.lower() or 'else:' in code.lower():
            score += 10
        if 'for ' in code.lower() or 'while ' in code.lower():
            score += 20
        if 'return' not in code.lower():
            score += 50
        
        # Penalize certain patterns
        if 'if else' in code.lower() or 'ternary' in code.lower():
            score += 30
        if 'print(' in code.lower():
            score += 5
        
        # Count lines (simpler is better)
        lines = code.strip().split('\n')
        score += len(lines) * 0.5
        
        # Model-specific biases (optional - based on historical performance)
        if model_name == 'gemini':
            score += 5  # Slight preference for local models
        elif model_name == 'deepseek':
            score += 10  # DeepSeek sometimes generates complex code
        
        return score
    
    def _check_syntax_with_detail(self, code: str) -> Tuple[bool, str]:
        """Check syntax and return detailed error message"""
        try:
            ast.parse(code)
            return True, "Valid"
        except SyntaxError as e:
            # Extract line and position info
            error_msg = f"{e.msg} at line {e.lineno}"
            if e.offset:
                error_msg += f", position {e.offset}"
            return False, error_msg
        except Exception as e:
            return False, str(e)
    
    def _extract_python_code(self, text: str) -> str:
        """Extract Python code from LLM response"""
        if not text:
            return ""
        
        # Look for code blocks first
        patterns = [
            r'```python\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                extracted = matches[0].strip()
                if extracted and 'def ' in extracted:
                    return extracted
        
        # If no code block, look for function definition
        lines = text.split('\n')
        function_start = -1
        function_lines = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                function_start = i
                function_lines.append(line)
                break
        
        if function_start >= 0:
            # Get the rest of the function
            for i in range(function_start + 1, len(lines)):
                current_line = lines[i]
                # Stop if we hit another def
                if current_line.strip().startswith('def '):
                    break
                function_lines.append(current_line)
            
            return '\n'.join(function_lines).strip()
        
        return text.strip()
    
    def get_selection_history(self) -> List[Dict]:
        """Get history of model selections"""
        return self.model_selection_history
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.clients.keys())