"""
Prompt engineering strategies for safety-critical code generation
"""
from typing import Dict, List, Optional
from config.llm_config import SYSTEM_PROMPTS, CODE_GENERATION_TEMPLATES

class PromptStrategies:
    """Collection of prompt strategies for different scenarios"""
    
    @staticmethod
    def get_system_prompt(safety_level: str = "SIL3") -> str:
        """Get system prompt based on safety level"""
        return SYSTEM_PROMPTS.get(safety_level, SYSTEM_PROMPTS["general"])
    
    @staticmethod
    def code_generation_prompt(requirement: str, 
                             safety_property: str,
                             variables: Dict[str, str],
                             previous_error: Optional[str] = None,
                             invariants: Optional[List[str]] = None) -> str:
        """Generate prompt for code generation"""
        
        if previous_error and invariants:
            # Refinement prompt with invariants
            return CODE_GENERATION_TEMPLATES["with_invariants"].format(
                requirement=requirement,
                invariants="\n".join(invariants),
                previous_error=previous_error
            )
        else:
            # Initial generation prompt
            var_desc = ", ".join([f"{name}: {type}" for name, type in variables.items()])
            
            return CODE_GENERATION_TEMPLATES["basic"].format(
                requirement=requirement,
                safety_property=safety_property,
                variables=var_desc
            )
    
    @staticmethod
    def counterexample_feedback_prompt(counterexample: Dict,
                                     violated_property: str) -> str:
        """Generate feedback prompt from counterexample"""
        
        ce_text = "\n".join([f"  {k} = {v}" for k, v in counterexample.items()])
        
        return f"""
        The previous code failed formal verification with this counterexample:
        
        Violating scenario:
        {ce_text}
        
        This violates the safety property: {violated_property}
        
        Please analyze why the code fails for this specific scenario and suggest corrections.
        Focus on the logical error that allows this violation.
        """
    
    @staticmethod
    def ensemble_voting_prompt(candidates: List[Dict]) -> str:
        """Generate prompt for ensemble voting/selection"""
        
        candidates_text = ""
        for i, candidate in enumerate(candidates, 1):
            candidates_text += f"\n\n--- Candidate {i} ---\n"
            candidates_text += f"Source: {candidate.get('model', 'unknown')}\n"
            candidates_text += f"Code:\n{candidate.get('code', '')}\n"
            candidates_text += f"Z3 Pre-Check Score: {candidate.get('z3_score', 0.0):.2f}"
        
        return f"""
        You are an expert safety engineer reviewing code candidates.
        
        Here are {len(candidates)} candidate implementations for the same requirement:
        {candidates_text}
        
        Analyze each candidate for:
        1. Correctness relative to requirements
        2. Clarity and maintainability
        3. Safety considerations
        4. Formal verifiability
        
        Select the best candidate and explain your choice.
        """
    
    @staticmethod
    def invariant_explanation_prompt(raw_invariants: List[str],
                                   code_context: str) -> str:
        """Generate prompt for explaining invariants"""
        
        invariants_text = "\n".join([f"- {inv}" for inv in raw_invariants])
        
        return f"""
        Explain these program invariants in the context of UAV safety:
        
        Code context: {code_context}
        
        Formal invariants:
        {invariants_text}
        
        For each invariant:
        1. Translate to natural language
        2. Explain its safety significance
        3. Suggest how to ensure it's maintained
        
        Provide clear, engineering-focused explanations.
        """