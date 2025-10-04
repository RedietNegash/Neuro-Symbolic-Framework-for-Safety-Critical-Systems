# safety_specification.py
from typing import Dict
from z3 import *

class SafetySpecification:
    def __init__(self, id: str, requirement: str, formal_property: str, variables: Dict, ambiguous_prompt: str = None):
        self.id = id
        self.requirement = requirement
        self.ambiguous_requirement = ambiguous_prompt or requirement 
        self.formal_property = formal_property
        self.variables = variables
        self.z3_vars = self._create_z3_variables()
    
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

def create_safety_specifications():
    """Create specifications designed to trigger common LLM logical errors"""
    return [
        SafetySpecification(
            id="drone_altitude_inclusive",
            requirement="The drone must maintain altitude between 40 and 60 meters, including both endpoints.",
            ambiguous_prompt="The drone must maintain altitude between 40 and 60 meters.",  
            formal_property="And(altitude >= 40, altitude <= 60)",
            variables={"altitude": "real"}
        ),
        SafetySpecification(
            id="drone_altitude_exclusive", 
            requirement="The drone must maintain altitude strictly between 40 and 60 meters (exclusive).",
            ambiguous_prompt="The drone must stay between 40 and 60 meters.", 
            formal_property="And(altitude > 40, altitude < 60)",
            variables={"altitude": "real"}
        ),
        SafetySpecification(
            id="robotic_grasp_safety",
            requirement="The robotic arm must never perform a Grasp action if the object is already held.",
            ambiguous_prompt="The robot should handle grasping objects safely.", 
            formal_property="Implies(action == StringVal('Grasp'), Not(is_holding))",
            variables={"is_holding": "bool", "action": "string"}
        ),
        SafetySpecification(
            id="speed_obstacle_conditional",
            requirement="The drone must reduce speed to under 10 m/s when any obstacle is within 20 meters.",
            ambiguous_prompt="The drone should slow down near obstacles.", 
            formal_property="Implies(distance < 20, speed <= 10)",
            variables={"speed": "real", "distance": "real"}
        ),
        SafetySpecification(
            id="battery_emergency", 
            requirement="The drone must initiate emergency landing when battery voltage drops below 11.1 volts.",
            ambiguous_prompt="The drone should land when battery is low.", 
            formal_property="Implies(voltage < 11.1, emergency_land == True)",
            variables={"voltage": "real", "emergency_land": "bool"}
        )
    ]