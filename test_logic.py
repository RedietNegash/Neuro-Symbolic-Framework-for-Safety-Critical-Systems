# test_logic.py
from safety_specification import create_safety_specifications
from z3 import *

def test_conditional_logic():
    """Test that our conditional logic is correct"""
    print("Testing conditional logic...")
    
    specs = create_safety_specifications()
    
    for spec in specs:
        print(f"\n{spec.id}: {spec.requirement}")
        print(f"Formal property: {spec.formal_property}")
        
        # Test some cases
        if spec.id == "manufacturing_speed_limit":
            print("\nTesting cases for manufacturing speed limit:")
            
            # Case 1: distance = 3 (< 5), speed = 1 (<= 2) -> should be safe (True)
            distance = Real('distance')
            speed = Real('speed')
            prop = Implies(distance < 5, speed <= 2)
            
            solver = Solver()
            solver.add(distance == 3, speed == 1)
            solver.add(prop)
            print(f"  distance=3, speed=1: {'Safe' if solver.check() == sat else 'Unsafe'}")
            
            # Case 2: distance = 3 (< 5), speed = 3 (> 2) -> should be unsafe
            solver = Solver()
            solver.add(distance == 3, speed == 3)
            solver.add(prop)
            print(f"  distance=3, speed=3: {'Safe' if solver.check() == sat else 'Unsafe'}")
            
            # Case 3: distance = 10 (>= 5), speed = 10 (any) -> should be safe
            solver = Solver()
            solver.add(distance == 10, speed == 10)
            solver.add(prop)
            print(f"  distance=10, speed=10: {'Safe' if solver.check() == sat else 'Unsafe'}")
        
        elif spec.id == "rotation_speed_limit":
            print("\nTesting cases for rotation speed limit:")
            
            distance = Real('distance')
            rotation_speed = Real('rotation_speed')
            prop = Implies(distance < 0.5, rotation_speed <= 5)
            
            # Case 1: distance = 0.3 (< 0.5), rotation_speed = 4 (<= 5) -> safe
            solver = Solver()
            solver.add(distance == 0.3, rotation_speed == 4)
            solver.add(prop)
            print(f"  distance=0.3, rotation_speed=4: {'Safe' if solver.check() == sat else 'Unsafe'}")
            
            # Case 2: distance = 0.3 (< 0.5), rotation_speed = 6 (> 5) -> unsafe
            solver = Solver()
            solver.add(distance == 0.3, rotation_speed == 6)
            solver.add(prop)
            print(f"  distance=0.3, rotation_speed=6: {'Safe' if solver.check() == sat else 'Unsafe'}")

if __name__ == "__main__":
    test_conditional_logic()