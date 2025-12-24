from src.verification.loop_invariant_synthesizer import LoopInvariantSynthesizer
from src.verification.safety_specification import SafetySpecification
import sys

# Mock Specification
spec = SafetySpecification(
    id="test_loop",
    requirement="Count must be positive",
    variables={"count": "int", "limit": "int"},
    formal_property="count > 0"
)

# Code with a loop
code = """
def check_safety(count, limit):
    for i in range(limit):
        count += 1
    return count > 0
"""

print("Testing LoopInvariantSynthesizer...")
synth = LoopInvariantSynthesizer()

# 1. Check Loop Detection
has_loops = synth._has_loops(code)
print(f"Has loops: {has_loops}")
if not has_loops:
    print("FAILED: Loop detection failed")
    sys.exit(1)

# 2. Check Traces
print("Executing traces...")
traces = synth._execute_traces(code, spec, num_traces=5)
print(f"Generated {len(traces)} traces")
if len(traces) == 0:
    print("FAILED: No traces generated")
    
# 3. Check Inference
print("Inferring invariants...")
invariants = synth._infer_ranges(traces)
print(f"Inferred: {invariants}")

# 4. Check Z3 Generation
from z3 import *
z3_vars = {"count": Int("count"), "limit": Int("limit")}
constraints = synth._naturalize_to_z3(invariants, z3_vars)
print(f"Z3 Constraints: {constraints}")

if constraints:
    print("PASSED: Generated constraints")
else:
    print("WARNING: No constraints generated (might be empty if inference was too loose)")
