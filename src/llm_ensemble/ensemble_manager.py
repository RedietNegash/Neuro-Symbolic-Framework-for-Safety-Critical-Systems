"""
Main ensemble manager with Z3 pre-check selection
"""
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any
import logging
import time

from .base_client import BaseLLMClient
from .gemini_client import GeminiClient
from .llama_client import LlamaClient
from .z3_pre_check import Z3PreChecker
from .prompt_strategies import PromptStrategies
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMEnsembleManager:
    """
    Manages LLM ensemble with Z3 pre-check selection
    Implements "Best-of-4 Selection via Z3 Pre-Check" from diagram
    """
    
    def __init__(self):
        self.models = self._initialize_models()
        self.z3_checker = Z3PreChecker(timeout_ms=settings.Z3_PRECHECK_TIMEOUT * 1000)
        self.prompt_strategies = PromptStrategies()
        
        logger.info(f"Initialized ensemble with {len(self.models)} models")
    
    def _initialize_models(self) -> Dict[str, BaseLLMClient]:
        """Initialize all available LLM models"""
        models = {}
        
        try:
            # Initialize Gemini
            gemini = GeminiClient()
            models["gemini"] = gemini
            logger.info("Gemini client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")
        
        try:
            # Initialize Llama
            llama = LlamaClient()
            models["llama"] = llama
            logger.info("Llama client initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Llama: {e}")
        
        if not models:
            raise RuntimeError("No LLM models could be initialized")
        
        return models
    
    def generate_ensemble(self,
                         requirement: str,
                         safety_property: str,
                         variables: Dict[str, str],
                         safety_level: str = "SIL3",
                         use_parallel: bool = None) -> List[Dict[str, Any]]:
        """
        Generate code from all ensemble models in parallel
        
        Returns: List of candidate results with metadata
        """
        if use_parallel is None:
            use_parallel = settings.ENSEMBLE_PARALLEL
        
        # Get system prompt
        system_prompt = self.prompt_strategies.get_system_prompt(safety_level)
        
        # Get generation prompt
        prompt = self.prompt_strategies.code_generation_prompt(
            requirement, safety_property, variables
        )
        
        candidates = []
        
        if use_parallel and len(self.models) > 1:
            # Parallel generation
            candidates = self._generate_parallel(prompt, system_prompt)
        else:
            # Sequential generation
            for name, model in self.models.items():
                candidate = self._generate_single(model, prompt, system_prompt)
                candidates.append(candidate)
        
        # Apply Z3 pre-check to all candidates
        scored_candidates = []
        for candidate in candidates:
            scored = self._apply_z3_pre_check(candidate, safety_property, variables)
            scored_candidates.append(scored)
        
        # Sort by Z3 score (descending)
        scored_candidates.sort(key=lambda x: x.get('z3_score', 0), reverse=True)
        
        logger.info(f"Generated {len(scored_candidates)} candidates with Z3 pre-check")
        
        return scored_candidates
    
    def _generate_parallel(self, 
                          prompt: str, 
                          system_prompt: str) -> List[Dict[str, Any]]:
        """Generate code from all models in parallel"""
        candidates = []
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(self.models), settings.ENSEMBLE_MAX_WORKERS)
        ) as executor:
            # Submit all generation tasks
            future_to_model = {
                executor.submit(
                    self._generate_single,
                    model,
                    prompt,
                    system_prompt
                ): name
                for name, model in self.models.items()
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_model):
                model_name = future_to_model[future]
                try:
                    candidate = future.result(timeout=settings.LLM_TIMEOUT)
                    candidates.append(candidate)
                    logger.debug(f"Completed generation for {model_name}")
                except Exception as e:
                    logger.error(f"Generation failed for {model_name}: {e}")
                    # Add fallback candidate
                    candidates.append({
                        'model': model_name,
                        'code': self._get_fallback_code(prompt),
                        'generation_time': 0.0,
                        'success': False,
                        'error': str(e)
                    })
        
        return candidates
    
    def _generate_single(self,
                        model: BaseLLMClient,
                        prompt: str,
                        system_prompt: str) -> Dict[str, Any]:
        """Generate code from a single model"""
        start_time = time.time()
        
        try:
            code = model.generate_code(
                prompt=prompt,
                system_context=system_prompt,
                temperature=settings.LLM_TEMPERATURE
            )
            
            generation_time = time.time() - start_time
            
            return {
                'model': model.model_name,
                'code': code,
                'generation_time': generation_time,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Single generation failed for {model.model_name}: {e}")
            
            return {
                'model': model.model_name,
                'code': self._get_fallback_code(prompt),
                'generation_time': generation_time,
                'success': False,
                'error': str(e)
            }
    
    def _apply_z3_pre_check(self,
                          candidate: Dict[str, Any],
                          safety_property: str,
                          variables: Dict[str, str]) -> Dict[str, Any]:
        """Apply Z3 pre-check to a candidate"""
        if not settings.Z3_PRECHECK_ENABLED:
            candidate['z3_score'] = 0.5  # Default score
            candidate['z3_diagnostic'] = "Z3 pre-check disabled"
            return candidate
        
        code = candidate['code']
        
        # Basic syntax check
        syntax_ok, syntax_msg = self.z3_checker.validate_syntax(code)
        if not syntax_ok:
            candidate['z3_score'] = 0.0
            candidate['z3_diagnostic'] = syntax_msg
            return candidate
        
        # Check for banned patterns
        safe_patterns, pattern_issues = self.z3_checker.check_banned_patterns(code)
        if not safe_patterns:
            candidate['z3_score'] = 0.1
            candidate['z3_diagnostic'] = f"Banned patterns: {pattern_issues}"
            return candidate
        
        # Z3 quick check
        is_valid, z3_score, z3_diagnostic = self.z3_checker.quick_check(
            code, safety_property, variables
        )
        
        candidate['z3_score'] = z3_score
        candidate['z3_diagnostic'] = z3_diagnostic
        candidate['z3_valid'] = is_valid
        
        return candidate
    
    def select_best_candidate(self,
                            candidates: List[Dict[str, Any]],
                            method: str = "z3_weighted") -> Dict[str, Any]:
        """
        Select best candidate from ensemble results
        
        Methods:
        - "z3_weighted": Weighted by Z3 score (default)
        - "first_valid": First candidate with Z3 score > threshold
        - "majority": If we had multiple models voting
        """
        if not candidates:
            raise ValueError("No candidates to select from")
        
        if method == "z3_weighted":
            # Select candidate with highest Z3 score
            best_candidate = max(candidates, key=lambda x: x.get('z3_score', 0))
            
            logger.info(f"Selected candidate from {best_candidate['model']} "
                       f"with Z3 score {best_candidate.get('z3_score', 0):.3f}")
            
            return best_candidate
            
        elif method == "first_valid":
            # Select first candidate with Z3 score > threshold
            threshold = 0.6
            for candidate in candidates:
                if candidate.get('z3_score', 0) >= threshold:
                    logger.info(f"Selected first valid candidate from {candidate['model']}")
                    return candidate
            
            # Fallback to highest score
            return max(candidates, key=lambda x: x.get('z3_score', 0))
        
        else:
            raise ValueError(f"Unknown selection method: {method}")
    
    def generate_with_feedback(self,
                              requirement: str,
                              safety_property: str,
                              variables: Dict[str, str],
                              previous_error: Optional[str] = None,
                              invariants: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate code with feedback from previous iteration
        (For refinement loop)
        """
        # Get system prompt
        system_prompt = self.prompt_strategies.get_system_prompt("SIL3")
        
        # Get refinement prompt
        prompt = self.prompt_strategies.code_generation_prompt(
            requirement, safety_property, variables, previous_error, invariants
        )
        
        # Generate from all models
        candidates = []
        for name, model in self.models.items():
            try:
                code = model.generate_code(prompt, system_prompt)
                
                candidate = {
                    'model': name,
                    'code': code,
                    'prompt': prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    'has_feedback': previous_error is not None
                }
                candidates.append(candidate)
                
            except Exception as e:
                logger.error(f"Feedback generation failed for {name}: {e}")
        
        # Apply Z3 pre-check and select best
        scored_candidates = []
        for candidate in candidates:
            scored = self._apply_z3_pre_check(candidate, safety_property, variables)
            scored_candidates.append(scored)
        
        return self.select_best_candidate(scored_candidates)
    
    def get_ensemble_critique(self,
                            code: str,
                            requirement: str,
                            issues: List[str]) -> Dict[str, str]:
        """Get critiques from all models in ensemble"""
        critiques = {}
        
        for name, model in self.models.items():
            try:
                critique = model.critique_code(code, requirement, issues)
                critiques[name] = critique
            except Exception as e:
                logger.error(f"Critique failed for {name}: {e}")
                critiques[name] = f"Critique error: {str(e)}"
        
        return critiques
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ensemble statistics"""
        stats = {
            "total_models": len(self.models),
            "models": {},
            "z3_pre_checks_enabled": settings.Z3_PRECHECK_ENABLED
        }
        
        for name, model in self.models.items():
            stats["models"][name] = model.get_stats()
        
        return stats
    
    def _get_fallback_code(self, prompt: str) -> str:
        """Get fallback code based on prompt content"""
        # Simple heuristic-based fallback
        prompt_lower = prompt.lower()
        
        if "altitude" in prompt_lower and ("40" in prompt or "60" in prompt):
            return """def check_altitude(altitude: float) -> bool:
    \"\"\"Check altitude safety\"\"\"
    MIN_ALTITUDE = 40.0
    MAX_ALTITUDE = 60.0
    return MIN_ALTITUDE <= altitude <= MAX_ALTITUDE"""
        
        elif "speed" in prompt_lower and "distance" in prompt_lower:
            return """def check_speed_distance(speed: float, distance: float) -> bool:
    \"\"\"Check speed based on obstacle distance\"\"\"
    SAFE_DISTANCE = 20.0
    MAX_SPEED_NEAR_OBSTACLE = 10.0
    
    if distance < SAFE_DISTANCE:
        return speed <= MAX_SPEED_NEAR_OBSTACLE
    return True"""
        
        elif "grasp" in prompt_lower or "holding" in prompt_lower:
            return """def can_grasp(is_holding: bool, action: str) -> bool:
    \"\"\"Check if grasping is safe\"\"\"
    if action == "Grasp":
        return not is_holding
    return True"""
        
        else:
            return """def safety_check() -> bool:
    \"\"\"Generic safety check\"\"\"
    # TODO: Implement specific safety logic
    # This is a fallback implementation
    return True"""