# safety_specification.py
from typing import Dict
from z3 import *

class SafetySpecification:
    """Represents a safety specification with formal properties"""
    
    def __init__(self, id: str, requirement: str, formal_property: str, variables: Dict):
        self.id = id
        self.requirement = requirement
        self.formal_property = formal_property
        self.variables = variables
        self.z3_vars = self._create_z3_variables()
    
    def _create_z3_variables(self) -> Dict:
        """Create Z3 variables from specification"""
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
    """Factory function to create safety specifications"""
    return [
        SafetySpecification(
            id="drone_altitude",
            requirement="The drone must maintain an altitude between 40 meters and 60 meters inclusive.",
            formal_property="And(altitude >= 40, altitude <= 60)",
            variables={"altitude": "real"}
        ),
        SafetySpecification(
            id="robotic_grasp",
            requirement="The robotic arm must never perform a Grasp action if the object is already held.",
            formal_property="Implies(action == StringVal('Grasp'), Not(is_holding))",
            variables={"is_holding": "bool", "action": "string"}
        ),
        SafetySpecification(
            id="drone_speed_obstacle",
            requirement="The drone's speed must never exceed 10 m/s when an obstacle is detected within 20 meters.",
            formal_property="Implies(distance < 20, speed <= 10)",
            variables={"speed": "real", "distance": "real"}
        ),
        SafetySpecification(
            id="battery_landing",
            requirement="The drone must initiate landing if battery voltage drops below 11.1 volts.",
            formal_property="Implies(voltage < 11.1, should_land == True)",
            variables={"voltage": "real", "should_land": "bool"}
        )
    ]