import ast
import random
from typing import Dict, List, Optional, Any, Set
from z3 import *
import asyncio

class LoopInvariantSynthesizer:
    """
    Synthesizes loop invariants to strengthen verification.
    Implements the 'Loop Invariant Synthesis' subgraph from the architecture:
    C -> D1 (Traces) -> D2 (Inference) -> D3 (Naturalization) -> D4 (Injection)
    
    Optimized to be lightweight.
    """
    
    def __init__(self):
        self.invariants = []
    
    def synthesize(self, code: str, specification: Any, llm_client: Any = None) -> List[Any]:
        """
        Main entry point: Synthesize invariants for the given code.
        Only runs if loops are detected.
        
        Args:
            code: The source code to analyze
            specification: Safety specification object
            llm_client: Optional LLM client for naturalization (D3). 
                        If provided, will be used to generate human-readable assertions.
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
        z3_constraints = self._naturalize_to_z3(invariants, specification.z3_vars, llm_client)
        
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
                
                try:
                    # We assume the function returns a boolean (Safe/Unsafe)
                    # We are interested in the inputs that lead to a "SAFE" state (True)
                    # Loop invariants usually constrain the properties that hold true throughout execution.
                    # Here we approximate by looking at inputs that produce safe outputs.
                    result = func(*args)
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
        Infers min/max ranges and simple relationships for variables.
        """
        safe_traces = [t for t in traces if t.get("_result") is True]
        if not safe_traces:
            return {}
            
        invariants = {}
        
        keys = [k for k in safe_traces[0].keys() if k != "_result"]
        
        # 1. Range Inference
        for key in keys:
            values = [t[key] for t in safe_traces]
            if not values: continue
            
            min_val = min(values)
            max_val = max(values)
            
            invariants[key] = {"min": min_val, "max": max_val, "type": "range"}
            
        # 2. Simple Relationship Inference (Lightweight)
        # Check if var1 < var2 always holds for specific variable pairs
        # We only check pairs to avoid combinatorial explosion (avoid consuming time)
        if len(keys) >= 2:
            import itertools
            # Limit to first 5 keys to keep it fast
            check_keys = keys[:5]
            for k1, k2 in itertools.combinations(check_keys, 2):
                if all(t[k1] < t[k2] for t in safe_traces):
                    invariants[f"{k1}_lt_{k2}"] = {"left": k1, "right": k2, "op": "<", "type": "relation"}
                elif all(t[k1] <= t[k2] for t in safe_traces):
                     invariants[f"{k1}_le_{k2}"] = {"left": k1, "right": k2, "op": "<=", "type": "relation"}

        return invariants

    def _naturalize_to_z3(self, invariants: Dict[str, Dict], z3_vars: Dict, llm_client: Any = None) -> List[Any]:
        """
        D3 -> D4: Convert inferred ranges to Z3 constraints.
        Uses LLM for naturalization if available, otherwise heuristics.
        """
        constraints = []
        
        # Fast path: Heuristics (Always run as base)
        for var_name, z3_var in z3_vars.items():
            if var_name in invariants and invariants[var_name]["type"] == "range":
                bounds = invariants[var_name]
                # Heuristic: If observed min >= 0, assume non-negativity (very common in physical systems)
                if bounds["min"] >= 0:
                     if "time" in var_name or "level" in var_name or "count" in var_name or "idx" in var_name:
                        constraints.append(z3_var >= 0)
        
        # Handle relational invariants
        for name, inv in invariants.items():
            if inv["type"] == "relation":
                left = z3_vars.get(inv["left"])
                right = z3_vars.get(inv["right"])
                if left is not None and right is not None:
                     if inv["op"] == "<": constraints.append(left < right)
                     elif inv["op"] == "<=": constraints.append(left <= right)

        # LLM Naturalization (Optional - Time constrained)
        # Only if explicitly provided and we have relational invariants that are non-trivial
        if llm_client and invariants:
            # To respect "not to consume time", we only call this if we have "interesting" invariants
            # or if the user explicitly configured it to be aggressive.
            # For now, we will skip it to be safe, or we could add a comment.
            # The prompt requested: "Update ... to optionally call an LLM ... passed via dependency injection"
            
            # We implement the call but user must enable it by passing the client.
            try:
                # Prepare a summary for the LLM
                summary_lines = []
                for name, inv in invariants.items():
                    if inv["type"] == "range":
                        summary_lines.append(f"{name}: observed range [{inv['min']}, {inv['max']}]")
                    elif inv["type"] == "relation":
                        summary_lines.append(f"Relationship: {inv['left']} {inv['op']} {inv['right']}")
                
                summary_text = "\n".join(summary_lines)
                
                # NOTE: Only call if we have meaningful data
                if summary_text and len(summary_lines) > 0:
                    prompt = f"""
                    Analyze these observed runtime traces for a UAV control system and suggest 1 or 2 LOGICAL invariants in Python math syntax.
                    
                    Observations:
                    {summary_text}
                    
                    STRICT RULES:
                    1. Return ONLY the boolean expression (e.g., 'alt >= 0').
                    2. Keep it simple and physically meaningful.
                    3. NO explanations.
                    4. One invariant per line.
                    """
                    
                    # Call the LLM
                    try:
                        response = llm_client.generate_code(prompt)
                        self._parse_llm_invariants(response, constraints, z3_vars)
                    except Exception as call_err:
                        print(f"    [Invariants] LLM call failed: {call_err}")
                        
            except Exception as e:
                print(f"    [Invariants] LLM Naturalization failed: {e}")

        return constraints

    def _parse_llm_invariants(self, response: str, constraints: List[Any], z3_vars: Dict):
        """Parse LLM response into Z3 constraints"""
        if not response: return
        
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('Here'): continue
            
            try:
                # Basic sanitization
                # Allow: alphanumeric, result, operators, spaces, parentheses
                clean_line = line.replace('`', '').replace('python', '')
                
                # Use Z3's python eval 
                # We expect simple expressions like 'alt >= 0'
                # We needs z3 vars in scope
                try:
                    # Provide z3_vars and Z3 functions to eval
                    eval_globals = {'And': And, 'Or': Or, 'Not': Not, 'Implies': Implies}
                    eval_globals.update(z3_vars)
                    
                    logic_expr = eval(clean_line, eval_globals, {})
                    if is_expr(logic_expr):
                        constraints.append(logic_expr)
                except:
                    pass
            except:
                pass
