import ast
import random
from typing import Dict, List, Optional, Any, Set
from z3 import *

class LoopInvariantSynthesizer:
    """
    Synthesizes loop invariants to strengthen verification.
    Implements the 'Loop Invariant Synthesis' subgraph from the architecture:
    C -> D1 (Traces) -> D2 (Inference) -> D3 (Naturalization) -> D4 (Injection)
    
    Optimized to be lightweight (not time consuming).
    """
    
    def __init__(self):
        self.invariants = []
    
    def synthesize(self, code: str, specification: Any) -> List[Any]:
        """
        Main entry point: Synthesize invariants for the given code.
        Only runs if loops are detected.
        """
        # 1. AST Check: Does it have loops?
        if not self._has_loops(code):
            return []
            
        print("    [Invariants] Loop detected. Synthesizing invariants...")
        
        # 2. D1: Execute Traces
        traces = self._execute_traces(code, specification, num_traces=20)
        
        # 3. D2: Inference (Simplified Daikon)
        invariants = self._infer_ranges(traces)
        
        # 4. D3 & D4: Naturalization & Z3 Constraint Generation
        z3_constraints = self._naturalize_to_z3(invariants, specification.z3_vars)
        
        if z3_constraints:
            print(f"    [Invariants] Injected {len(z3_constraints)} strengthened constraints")
            
        return z3_constraints

    def _has_loops(self, code: str) -> bool:
        """Check if code contains loops"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    return True
        except:
            pass
        return False
        
    def _execute_traces(self, code: str, specification: Any, num_traces: int = 10) -> List[Dict[str, Any]]:
        """
        D1: Execute Test Traces in Sandbox
        Runs the code with random inputs to gather variable states.
        """
        traces = []
        param_names = list(specification.variables.keys())
        
        # Define a safe execution scope
        local_scope = {}
        
        # Extract the function definition to call it
        try:
            exec(code, {}, local_scope)
            func_name = [k for k, v in local_scope.items() if callable(v)][0]
            func = local_scope[func_name]
            
            for _ in range(num_traces):
                # Generate random inputs based on probable types
                args = []
                trace_snapshot = {}
                
                for var, type_hint in specification.variables.items():
                    if type_hint == "real" or "float" in str(type_hint):
                        val = random.uniform(0, 100) # Assumption: positive range often safe
                        if "altitude" in var: val = random.uniform(30, 70)
                        if "lat" in var: val = random.uniform(-90, 90)
                    else: 
                        val = random.randint(0, 100)
                        if "battery" in var: val = random.randint(0, 20)
                        
                    args.append(val)
                    trace_snapshot[var] = val
                
                # Run function (ignoring result, we just want to see if it crashes)
                # Note: In a real Daikon setup, we'd instrument the code to trace INTERMEDIATE values.
                # For this lightweight version, we trace INPUTS that led to safe/unsafe returns?
                # actually, simpler: Just trace the inputs. The invariant is often about the relation between inputs.
                # Logic: If function returns True (Safe), what holds true for the inputs?
                
                try:
                    result = func(*args)
                    # We only care about traces where the code says "Safe" (True) or "Unsafe" (False)
                    # Loop invariants usually constrain the STATE.
                    # Since we are verifying a function, the "State" is the arguments.
                    # We record the trace.
                    trace_snapshot["_result"] = result
                    traces.append(trace_snapshot)
                except:
                    continue
                    
        except Exception as e:
            # print(f"Trace execution failed: {e}")
            pass
            
        return traces

    def _infer_ranges(self, traces: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """
        D2: Inference (Simplified)
        Infers min/max ranges for variables for TRACES THAT RETURNED TRUE (Safe).
        Hypothesis: "Safe states imply these bounds"
        """
        safe_traces = [t for t in traces if t.get("_result") is True]
        if not safe_traces:
            return {}
            
        invariants = {}
        
        # Iterate over all variables except _result
        keys = [k for k in safe_traces[0].keys() if k != "_result"]
        
        for key in keys:
            values = [t[key] for t in safe_traces]
            if not values: continue
            
            min_val = min(values)
            max_val = max(values)
            
            invariants[key] = {"min": min_val, "max": max_val}
            
        return invariants

    def _naturalize_to_z3(self, invariants: Dict[str, Dict], z3_vars: Dict) -> List[Any]:
        """
        D3 -> D4: Convert inferred ranges to Z3 constraints.
        """
        constraints = []
        
        # 1. Basic Invariant: Non-negativty for typical physical quantities/counters
        # This is a safe "heuristic" invariant that often helps solvers avoid -1 loops
        for var_name, z3_var in z3_vars.items():
            if "count" in var_name.lower() or "idx" in var_name.lower() or "step" in var_name.lower():
                constraints.append(z3_var >= 0)
            
            # If traces showed strictly positive values, propose it as an invariant
            if var_name in invariants:
                bounds = invariants[var_name]
                if bounds["min"] >= 0:
                     if "time" in var_name or "level" in var_name: # Heuristic for likely positive physical vars
                        constraints.append(z3_var >= 0)

        return constraints
