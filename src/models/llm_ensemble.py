# src/models/llm_ensemble.py
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import ast
import re

# Import from current module
from .llm_client import GeminiLLMClient
from .llm_client_llama import LlamaLLMClient
from .llm_client_deepseek import DeepSeekLLMClient
from ..core import config

class LLMEnsemble:
    """Orchestrates an ensemble of LLMs for verified code synthesis with tracking"""
    
    def __init__(self, include_gemini: bool = True):
        self.clients = {}
        
        # Initialize models with error handling
        try:
            self.clients["llama"] = LlamaLLMClient(
                model=config.LLAMA_MODEL, 
                host=config.LLAMA_HOST
            )
            print("[OK] Llama client initialized")
        except Exception as e:
            print(f"[Warning] Failed to initialize Llama: {e}")
        
        try:
            # Use the correct DeepSeek model name
            deepseek_model = config.DEEPSEEK_MODEL
            print(f"[Info] Using DeepSeek model: {deepseek_model}")
            self.clients["deepseek"] = DeepSeekLLMClient(
                model=deepseek_model, 
                host=config.DEEPSEEK_HOST
            )
            print("[OK] DeepSeek client initialized")
        except Exception as e:
            print(f"[Warning] Failed to initialize DeepSeek: {e}")
        
        # Add Gemini if available (Commented out to save time)
        # if include_gemini and config.GEMINI_API_KEY:
        #     try:
        #         self.clients["gemini"] = GeminiLLMClient(
        #             model=config.GEMINI_MODEL, 
        #             api_key=config.GEMINI_API_KEY
        #         )
        #         print("[OK] Gemini added to ensemble")
        #     except Exception as e:
        #         print(f"[Warning] Could not add Gemini to ensemble: {e}")
        #         print("Continuing with available models")
        
        if not self.clients:
            raise RuntimeError("No LLM clients could be initialized")
            
        self.logs = []
        self.last_selected_model = None
        self.model_selection_history = []
        print(f"[Ready] Ensemble initialized with {len(self.clients)} models: {', '.join(self.clients.keys())}")
    
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

    def arbitrate(self, candidates: Dict[str, str], 
                 verifier_callback: Optional[Any] = None, 
                 specification: Optional[Any] = None) -> Optional[str]:
        """Select the best candidate based on Z3 pre-check and simplicity"""
        valid_candidates = {}
        candidate_scores = {}
        
        print(f"    Evaluating {len(candidates)} candidates...")
        
        for name, code in candidates.items():
            if not code:
                # print(f"    [{name.upper()}] no code generated")
                continue
            
            clean_code = self._extract_python_code(code)
            if not clean_code:
                # print(f"    [{name.upper()}] no Python code found")
                continue
            
            # 1. Syntax Check (Fast)
            syntax_valid, error_msg = self._check_syntax_with_detail(clean_code)
            if not syntax_valid:
                print(f"    [{name.upper()}] Syntax Error: {error_msg}")
                continue
                
            # 2. Calculate Base Score (Simplicity)
            score = self._calculate_code_score(clean_code, name)
            
            # 3. Z3 Pre-Check (Architectural Requirement: 64.3% -> 91.0%)
            z3_status = "Skipped"
            if verifier_callback and specification:
                try:
                    is_safe, _ = verifier_callback(clean_code, specification)
                    if is_safe:
                        score -= 500  # Massive bonus for verified safety
                        z3_status = "PASS"
                    else:
                        score += 500  # Penalty for proven unsafe
                        z3_status = "FAIL"
                except Exception as e:
                    z3_status = f"Error: {e}"
            
            candidate_scores[name] = score
            valid_candidates[name] = clean_code
            
            print(f"    [{name.upper()}] Score: {score:.1f} | Syntax: OK | Z3 Pre-Check: {z3_status}")

        if not valid_candidates:
            print("    No valid candidates found")
            return None
        
        # Select best candidate (lowest score is best)
        best_name = min(candidate_scores.items(), key=lambda x: x[1])[0]
        best_code = valid_candidates[best_name]
        
        self.last_selected_model = best_name
        
        # Track history
        self.model_selection_history.append({
            "selected_model": best_name,
            "all_scores": candidate_scores,
            "candidates": list(valid_candidates.keys()),
            "timestamp": asyncio.get_event_loop().time()
        })
        
        print(f"    >>> Selected {best_name.upper()} (Score: {candidate_scores[best_name]:.1f})")
        return best_code
    
    def _calculate_code_score(self, code: str, model_name: str) -> float:
        """Calculate score for code quality (lower is better)"""
        score = len(code) * 0.01  # Penalize length
        
        # Penalize complex constructs
        if 'if ' in code.lower(): score += 10
        if 'elif ' in code.lower(): score += 10
        if 'while ' in code.lower(): score += 20
        
        # Penalize bad patterns
        if 'print(' in code.lower(): score += 5
        
        # Model bias (optional)
        if model_name == 'gemini': score -= 5
        
        return score

    def _check_syntax_with_detail(self, code: str) -> Tuple[bool, str]:
        """Check syntax and return detailed error message"""
        try:
            ast.parse(code)
            return True, "Valid"
        except SyntaxError as e:
            return False, f"{e.msg} at line {e.lineno}"
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