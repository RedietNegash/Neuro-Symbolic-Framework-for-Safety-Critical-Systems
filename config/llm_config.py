"""
LLM-specific configuration and prompt templates
"""
from typing import Dict, List

# System prompts for different safety levels
SYSTEM_PROMPTS = {
    "SIL3": """You are a DO-178C Level B certified avionics engineer specializing in UAV control logic.
Your code must be:
1. Deterministic and verifiable
2. Include explicit safety checks
3. Handle edge cases and faults
4. Use minimal dependencies
5. Follow MISRA C-like Python guidelines""",
    
    "general": """You are a safety-critical systems engineer.
Generate Python code that is:
- Correct by construction
- Easy to formally verify
- Free from side effects
- Well-commented for verification"""
}

# Safety property templates for Z3 integration
SAFETY_TEMPLATES = {
    "range_check": "And({var} >= {min}, {var} <= {max})",
    "implication": "Implies({condition}, {consequence})",
    "equality": "{var} == {value}",
    "inequality": "{var} != {value}"
}

# Code generation templates
CODE_GENERATION_TEMPLATES = {
    "basic": """Generate a Python function for this safety requirement:
REQUIREMENT: {requirement}
SAFETY PROPERTY (Z3 format): {safety_property}
VARIABLES: {variables}

Constraints:
- Function must return boolean (True if safe, False if violation)
- No external dependencies
- Use if/else for control flow
- Include type hints

Generate ONLY the Python function:""",
    
    "with_invariants": """Generate Python code with these learned invariants:
REQUIREMENT: {requirement}
INVARIANTS: {invariants}
PREVIOUS ERROR: {previous_error}

Generate corrected code that respects all invariants:"""
}

# Z3 pre-check validation rules
Z3_PRE_CHECK_RULES = {
    "required_keywords": ["def ", "return ", ":"],
    "banned_patterns": ["input()", "eval(", "exec(", "__import__"],
    "max_function_length": 50,  # lines
    "required_variable_match": True
}