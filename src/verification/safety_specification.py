# safety_specification.py - SIMPLIFIED VERSION
from typing import Dict, List
from z3 import *

class SafetySpecification:
    """Represents a safety specification with formal properties"""
    
    def __init__(self, id: str, requirement: str, formal_property: str, variables: Dict, 
                 mission_goals: List[str] = None, safety_invariants: List[str] = None):
        self.id = id
        self.requirement = requirement
        self.formal_property = formal_property
        self.variables = variables
        self.mission_goals = mission_goals or []
        self.safety_invariants = safety_invariants or []
        self.z3_vars = self._create_z3_variables()

    def to_json(self) -> Dict:
        """Export specification to structured JSON"""
        return {
            "id": self.id,
            "requirement": self.requirement,
            "mission_goals": self.mission_goals,
            "safety_invariants": self.safety_invariants,
            "formal_property": self.formal_property,
            "variables": self.variables
        }
    
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
    """Factory function to create SIMPLIFIED safety specifications"""
    return [
        SafetySpecification(
            id="drone_altitude",
            requirement="The drone altitude must be between 40 and 60 meters.",
            formal_property="And(altitude >= 40, altitude <= 60)",
            variables={"altitude": "real"},
            mission_goals=["Maintain safe altitude"],
            safety_invariants=["Altitude bounds"]
        ),
        SafetySpecification(
            id="execution_time_limit",
            requirement="The execution time must be 10 or less.",
            formal_property="execution_time <= 10",
            variables={"execution_time": "int"},
            mission_goals=["Meet timing requirements"],
            safety_invariants=["Timing constraint"]
        ),
        SafetySpecification(
            id="fault_tolerance",
            requirement="If IMU1 fails, active IMU must be 2.",
            formal_property="Implies(imu1_failed, active_imu == 2)",
            variables={"imu1_failed": "bool", "active_imu": "int"},
            mission_goals=["Handle failures"],
            safety_invariants=["Redundancy"]
        ),
        SafetySpecification(
            id="velocity_difference",
            requirement="GPS and IMU velocities must differ by at most 2.0.",
            formal_property="Abs(gps_vel - imu_vel) <= 2.0",
            variables={"gps_vel": "real", "imu_vel": "real"},
            mission_goals=["Maintain sensor consistency"],
            safety_invariants=["Sensor fusion"]
        ),
        SafetySpecification(
            id="invalid_signature",
            requirement="If signature is invalid, action must be 'None'.",
            formal_property="Implies(Not(is_signature_valid), action == StringVal('None'))",
            variables={"is_signature_valid": "bool", "action": "string"},
            mission_goals=["Ensure security"],
            safety_invariants=["Authentication"]
        ),
        SafetySpecification(
            id="low_battery",
            requirement="If battery is below 15, command must be 'RTH'.",
            formal_property="Implies(battery_level < 15, command == StringVal('RTH'))",
            variables={"battery_level": "int", "command": "string"},
            mission_goals=["Safe operation"],
            safety_invariants=["Power management"]
        ),
        SafetySpecification(
            id="memory_usage",
            requirement="Heap usage must be 80 or less.",
            formal_property="heap_usage <= 80",
            variables={"heap_usage": "int"},
            mission_goals=["Prevent overflow"],
            safety_invariants=["Memory safety"]
        )
    ]