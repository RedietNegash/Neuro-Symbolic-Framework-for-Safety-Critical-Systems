# safety_specification.py
from typing import Dict, List, Tuple
from z3 import *
import ast
import random

class SafetySpecification:
    def __init__(self, id: str, requirement: str, formal_property: str, variables: Dict, 
                 ambiguous_prompt: str = None, correct_python_code: str = None):
        self.id = id
        self.requirement = requirement
        self.ambiguous_requirement = ambiguous_prompt or requirement 
        self.formal_property = formal_property
        self.variables = variables
        self.z3_vars = self._create_z3_variables()
        self.correct_python_code = correct_python_code
    
    def _create_z3_variables(self) -> Dict:
        z3_vars = {}
        for var_name, var_type in self.variables.items():
            if var_type == "int":
                z3_vars[var_name] = Int(var_name)
            elif var_type == "real":
                z3_vars[var_name] = Real(var_name)
            elif var_type == "bool":
                z3_vars[var_name] = Bool(var_name)
            elif var_type == "string":
                z3_vars[var_name] = String(var_name)
            else:
                z3_vars[var_name] = Real(var_name)
        return z3_vars

class BugInjector:
    """Systematically injects logical errors into code to mimic LLM 'near-miss' errors"""
    
    @staticmethod
    def inject_boundary_error(code: str) -> str:
        """Inject off-by-one and boundary errors"""
        mutations = [
            (">=", ">"),   # inclusive to exclusive
            ("<=", "<"),   # inclusive to exclusive
            (">", ">="),   # exclusive to inclusive  
            ("<", "<="),   # exclusive to inclusive
            ("==", "!="),  # equality to inequality
            ("and", "or"), # logical AND to OR
        ]
        
        for original, mutated in mutations:
            if original in code:
                return code.replace(original, mutated)
        return code
    
    @staticmethod
    def inject_condition_error(code: str) -> str:
        """Inject conditional logic errors"""
        if "if" in code and "else" in code:
            lines = code.split('\n')
            if_lines = [i for i, line in enumerate(lines) if 'if' in line and ':' in line]
            if if_lines:
                idx = if_lines[0]
                return code.replace("if", "if not").replace("not not", "")
        return code
    
    @staticmethod
    def inject_operator_error(code: str) -> str:
        """Inject operator errors"""
        mutations = [
            ("+", "-"), ("-", "+"), ("*", "/"), ("/", "*"),
            ("+ 1", "- 1"), ("- 1", "+ 1")
        ]
        
        for original, mutated in mutations:
            if original in code:
                return code.replace(original, mutated)
        return code

class DatasetGenerator:
    """Generates ground truth dataset as described in Section 2.1"""
    
    @staticmethod
    def generate_ground_truth_dataset() -> List[Tuple[SafetySpecification, str]]:
        """Create dataset with correct and buggy code variants"""
        dataset = []
        
        specifications = create_safety_specifications()
        
        for spec in specifications:
            if spec.correct_python_code:
                dataset.append((spec, spec.correct_python_code, "correct"))
                
                buggy_variants = [
                    BugInjector.inject_boundary_error(spec.correct_python_code),
                    BugInjector.inject_condition_error(spec.correct_python_code),
                    BugInjector.inject_operator_error(spec.correct_python_code)
                ]
                
                for i, buggy_code in enumerate(buggy_variants):
                    if buggy_code != spec.correct_python_code:
                        buggy_spec = SafetySpecification(
                            id=f"{spec.id}_buggy_{i}",
                            requirement=spec.requirement,
                            formal_property=spec.formal_property,
                            variables=spec.variables,
                            ambiguous_prompt=spec.ambiguous_requirement,
                            correct_python_code=buggy_code
                        )
                        dataset.append((buggy_spec, buggy_code, "buggy"))
        
        return dataset



def create_safety_specifications():
    """Create specifications following exact document examples from Section 2.1 table"""
    return [
        SafetySpecification(
            id="drone_altitude",
            requirement="The drone's altitude must always be between 40m and 60m in 'AltHold' mode.",
            ambiguous_prompt="The drone must maintain altitude between 40 and 60 meters.",
            formal_property="And(altitude >= 40, altitude <= 60)",
            variables={"altitude": "real"},
            correct_python_code="def check_altitude(alt):\n    return 40 <= alt <= 60"
        ),
        SafetySpecification(
            id="speed_obstacle", 
            requirement="The drone's speed must never exceed 10m/s when an obstacle is detected within 20m.",
            ambiguous_prompt="The drone should slow down near obstacles.",
            formal_property="Implies(distance < 20, speed <= 10)",
            variables={"speed": "real", "distance": "real"},
            correct_python_code="def safe_speed(speed, distance):\n    if distance < 20:\n        return speed <= 10\n    return True"
        ),

        SafetySpecification(
            id="robotic_grasp",
            requirement="The robotic arm must never perform a Grasp action if the object is already held.",
            ambiguous_prompt="The robot should handle grasping objects safely.",
            formal_property="Implies(action_is_Grasp == True, Not(is_holding))", 
            variables={"is_holding": "bool", "action_is_Grasp": "bool"},
            correct_python_code="""def can_grasp(is_holding, action_is_Grasp):
            return not (action_is_Grasp and is_holding)"""
        )
    ]