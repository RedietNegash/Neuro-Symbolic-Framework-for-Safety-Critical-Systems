# safety_specification.py
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from z3 import *
import ast
import random

@dataclass
class TaskSpecification:
    """Enhanced task specification for real-time UAV systems"""
    name: str
    priority: int
    period: float
    wcet: float
    deadline: float
    jitter: float = 0.0
    memory_usage: int = 0
    stack_size: int = 0

class RealTimeSchedulingAnalyzer:
    """
    Comprehensive real-time scheduling analysis for UAV systems
    """
    
    @staticmethod
    def rate_monotonic_analysis(tasks: List[TaskSpecification]) -> Tuple[bool, float]:
        """Liu & Layland RMS utilization bound test"""
        sorted_tasks = sorted(tasks, key=lambda x: x.period)
        total_utilization = sum(task.wcet / task.period for task in sorted_tasks)
        n = len(sorted_tasks)
        utilization_bound = n * (2 ** (1/n) - 1)
        
        if total_utilization <= utilization_bound:
            return True, total_utilization
        return RealTimeSchedulingAnalyzer.response_time_analysis(sorted_tasks), total_utilization
    
    @staticmethod
    def response_time_analysis(tasks: List[TaskSpecification]) -> bool:
        """Exact response time analysis with jitter and overhead"""
        for i, task in enumerate(tasks):
            hp_tasks = tasks[:i]
            response_time = task.wcet + task.jitter
            
            for _ in range(100):  # Convergence limit
                interference = sum(
                    math.ceil((response_time + hp_task.jitter) / hp_task.period) * hp_task.wcet 
                    for hp_task in hp_tasks
                )
                new_response_time = task.wcet + interference + task.jitter
                
                if abs(new_response_time - response_time) < 0.001:
                    break
                if new_response_time > task.deadline:
                    return False
                response_time = new_response_time
                
            if response_time > task.deadline:
                return False
        return True

class SafetySpecification:
    def __init__(self, id: str, requirement: str, formal_property: str, variables: Dict, 
                 ambiguous_prompt: str = None, correct_python_code: str = None, 
                 task_set=None, safety_level: str = "SIL3", standard: str = "IEC61508"):
        self.id = id
        self.requirement = requirement
        self.ambiguous_requirement = ambiguous_prompt or requirement 
        self.formal_property = formal_property
        self.variables = variables
        self.z3_vars = self._create_z3_variables()
        self.task_set = task_set 
        self.is_temporal = task_set is not None
        self.correct_python_code = correct_python_code
        self.safety_level = safety_level
        self.standard = standard

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
                z3_vars[var_name] = Real(var_name)  # Default to real
        return z3_vars

def create_safety_specifications():
    """Create specifications with FIXED variable definitions"""
    
    specifications = []
    # 1. TIMING DETERMINISM AND REAL-TIME SCHEDULING - FIXED
    wcet_spec = SafetySpecification(
        id="wcet_validation_sil3",
        requirement="All critical UAV control tasks must have rigorously measured WCET values validated on target hardware with 95% confidence interval.",
        # FIXED: Use individual variables instead of lists
        formal_property="And(Validation_Confidence >= 0.95, Measured_WCET_1 >= Actual_WCET_1, Measured_WCET_2 >= Actual_WCET_2, Measured_WCET_3 >= Actual_WCET_3)",
        # FIXED: Define individual variables instead of lists
        variables={
            "Measured_WCET_1": "real",
            "Measured_WCET_2": "real", 
            "Measured_WCET_3": "real",
            "Actual_WCET_1": "real",
            "Actual_WCET_2": "real",
            "Actual_WCET_3": "real",
            "Validation_Confidence": "real"
        },
        safety_level="SIL3",
        standard="IEC61508",
        correct_python_code="""def verify_wcet_validation(measured_wcet_1, measured_wcet_2, measured_wcet_3, 
                          actual_wcet_1, actual_wcet_2, actual_wcet_3, validation_confidence):
    \"\"\"Verify WCET validation meets safety requirements\"\"\"
    confidence_ok = validation_confidence >= 0.95
    wcet_1_ok = measured_wcet_1 >= actual_wcet_1
    wcet_2_ok = measured_wcet_2 >= actual_wcet_2  
    wcet_3_ok = measured_wcet_3 >= actual_wcet_3
    return confidence_ok and wcet_1_ok and wcet_2_ok and wcet_3_ok"""
    )

    specifications.append(wcet_spec) 

    # 2. FAULT TOLERANCE AND REDUNDANCY - FIXED STRUCTURE

    sensor_spec = SafetySpecification(
        id="sensor_redundancy_failover",
        requirement="Primary IMU failure must trigger automatic failover to redundant IMU within 5ms with validated sensor consistency.",
        formal_property="Implies(And(Primary_IMU_Fault, Not(Redundant_IMU_Fault)), And(Failover_Time <= 0.005, Sensor_Consistency))",
        variables={
            "Primary_IMU_Fault": "bool",
            "Redundant_IMU_Fault": "bool", 
            "Failover_Time": "real",
            "Sensor_Consistency": "bool"
        },
        correct_python_code="""def sensor_failover_logic(primary_fault, redundant_fault, failover_time, sensor_consistency):
        \"\"\"Verify sensor failover meets timing and consistency requirements\"\"\"
        if primary_fault and not redundant_fault:
            return failover_time <= 0.005 and sensor_consistency
        return True"""
    )
    specifications.append(sensor_spec)  

    processor_spec = SafetySpecification(
        id="processor_redundancy_do254",
        requirement="Primary flight computer failure must trigger redundant computer activation within 50ms with complete state synchronization.",
        formal_property="Implies(Primary_FCU_Failed, And(Redundant_Active, Failover_Time <= 0.05))",
        variables={
            "Primary_FCU_Failed": "bool",
            "Redundant_Active": "bool",
            "Failover_Time": "real",
            "State_Synchronized": "bool"
        },
        standard="DO-254",
        correct_python_code="""def processor_failover_validation(primary_failed, redundant_active, failover_time, state_synced):
    \"\"\"Validate processor redundancy failover\"\"\"
    if primary_failed:
        return redundant_active and failover_time <= 0.05 and state_synced
    return True"""
    )
    specifications.append(processor_spec)  

    # 3. SENSOR FUSION INTEGRITY
    fusion_spec = SafetySpecification(
        id="multi_sensor_consistency",
        requirement="Fused sensor outputs must maintain consistency across GPS, IMU, and vision systems with outlier rejection for fault detection.",
        formal_property="And(Abs(Sensor_GPS - Fused_Output) <= Tolerance, Abs(Sensor_IMU - Fused_Output) <= Tolerance, Abs(Sensor_Vision - Fused_Output) <= Tolerance)",
        variables={
            "Sensor_GPS": "real",
            "Sensor_IMU": "real",
            "Sensor_Vision": "real", 
            "Fused_Output": "real",
            "Tolerance": "real"
        },
        correct_python_code="""def validate_sensor_consistency(gps, imu, vision, fused, tolerance=2.0):
    \"\"\"Validate sensor fusion consistency\"\"\"
    return (abs(gps - fused) <= tolerance and 
            abs(imu - fused) <= tolerance and 
            abs(vision - fused) <= tolerance)"""
    )
    specifications.append(fusion_spec)  

    # 4. COMMUNICATION RELIABILITY AND SECURITY
    comms_spec = SafetySpecification(
        id="critical_command_latency",
        requirement="Emergency stop commands must reach actuators within 100ms with 99.9% reliability under maximum network load.",
        formal_property="Implies(Is_Emergency_Stop, And(Latency <= 0.1, Reliability >= 0.999))",
        variables={
            "Is_Emergency_Stop": "bool", 
            "Latency": "real",
            "Reliability": "real"
        },
        correct_python_code="""def validate_emergency_latency(is_emergency_stop, latency, reliability):
        \"\"\"Validate emergency command latency and reliability\"\"\"
        if is_emergency_stop:
            return latency <= 0.1 and reliability >= 0.999
        return True"""
    )
    specifications.append(comms_spec)

    # 5. POWER AND THERMAL MANAGEMENT
    battery_spec = SafetySpecification(
        id="battery_fail_safe",
        requirement="Critical battery level (below 20%) must trigger return-to-home with power consumption optimization.",
        formal_property="Implies(Battery_Level <= 20, And(RTH_Initiated, Power_Saving_Mode))",
        variables={
            "Battery_Level": "real",
            "RTH_Initiated": "bool", 
            "Power_Saving_Mode": "bool"
        },
        correct_python_code="""def battery_safety_check(battery_level, rth_initiated, power_saving):
    \"\"\"Check battery safety conditions\"\"\"
    if battery_level <= 20:
        return rth_initiated and power_saving
    return True"""
    )
    specifications.append(battery_spec)  

    thermal_spec = SafetySpecification(
        id="thermal_overload_protection",
        requirement="CPU temperature above 85°C must trigger thermal throttling and emergency procedures if sustained.",
        formal_property="Implies(CPU_Temp > 85, Thermal_Throttling)",
        variables={
            "CPU_Temp": "real",
            "Thermal_Throttling": "bool"
        },
        correct_python_code="""def thermal_safety_check(cpu_temp, thermal_throttling):
    \"\"\"Verify thermal protection is active when needed\"\"\"
    if cpu_temp > 85:
        return thermal_throttling
    return True"""
    )
    specifications.append(thermal_spec) 

    # 6. BASIC SAFETY SCENARIOS (from original paper)
    alt_spec = SafetySpecification(
        id="drone_altitude",
        requirement="The drone's altitude must always be between 40m and 60m in 'AltHold' mode.",
        ambiguous_prompt="The drone must maintain altitude between 40 and 60 meters.",
        formal_property="And(altitude >= 40, altitude <= 60)",
        variables={"altitude": "real"},
        correct_python_code="def check_altitude(alt):\n    return 40 <= alt <= 60"
    )
    specifications.append(alt_spec)  

    speed_spec = SafetySpecification(
        id="speed_obstacle", 
        requirement="The drone's speed must never exceed 10m/s when an obstacle is detected within 20m.",
        ambiguous_prompt="The drone should slow down near obstacles.",
        formal_property="Implies(distance < 20, speed <= 10)",
        variables={"speed": "real", "distance": "real"},
        correct_python_code="def safe_speed(speed, distance):\n    if distance < 20:\n        return speed <= 10\n    return True"
    )
    specifications.append(speed_spec)  

    robotic_spec = SafetySpecification(
        id="robotic_grasp",
        requirement="The robotic arm must never perform a Grasp action if the object is already held.",
        ambiguous_prompt="The robot should handle grasping objects safely.", 
        formal_property="Implies(action_is_Grasp == True, Not(is_holding))",
        variables={"is_holding": "bool", "action_is_Grasp": "bool"},
        correct_python_code="""def can_grasp(is_holding, action_is_Grasp):
    return not (action_is_Grasp and is_holding)"""
    )
    specifications.append(robotic_spec)  

    return specifications

