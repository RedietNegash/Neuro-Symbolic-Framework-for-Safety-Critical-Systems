# neuro_symbolic_verifier.py
from typing import Dict, List, Optional, Any, Tuple
from z3 import *
import time
from symbolic_bridge import ASTToZ3Translator
from safety_specification import SafetySpecification


class FormalVerifier:
    """
    Formal Verification Component using SMT Solver
    """
    
    def __init__(self):
        self.solver = z3.Solver()
        self.translator = ASTToZ3Translator()
    
    def verify_safety_property(self, python_code: str, safety_property: str, 
                            specification_vars: Dict) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # STEP 1: Create Z3 variables FIRST
            z3_vars = {}
            for var_name, var_type in specification_vars.items():
                if var_type == "int":
                    z3_vars[var_name] = Int(var_name)
                elif var_type == "real":
                    z3_vars[var_name] = Real(var_name)
                elif var_type == "bool":
                    z3_vars[var_name] = Bool(var_name)
            
            # STEP 2: Pass Z3 variables to translator so it uses the SAME variables
            code_z3_expr = self.translator.python_code_to_z3(python_code, z3_vars)
            
            # STEP 3: Create safety property using the SAME Z3 variables
            safety_z3 = eval(safety_property, globals(), z3_vars)
            
            print(f"DEBUG: Code expression type: {type(code_z3_expr)}")
            print(f"DEBUG: Code expression: {code_z3_expr}")
            print(f"DEBUG: Safety property: {safety_z3}")
            
            # STEP 4: Check if code and safety property are EQUIVALENT
            # If they differ for any input, that's a violation
            equivalence_check = (code_z3_expr != safety_z3)
            
            self.solver.reset()
            self.solver.add(equivalence_check)
            
            result = self.solver.check()
            
            verification_time = time.time() - start_time
            
            if result == z3.unsat:
                # Cannot find inputs where they differ -> equivalent -> VERIFIED
                return {
                    'verified': True,
                    'counterexample': None,
                    'reason': 'Property always holds',
                    'verification_time': verification_time
                }
            elif result == z3.sat:
                # Found inputs where they differ -> NOT equivalent -> VIOLATION
                model = self.solver.model()
                counterexample = self._extract_counterexample(model, z3_vars)
                return {
                    'verified': False,
                    'counterexample': counterexample,
                    'reason': 'Property violation found',
                    'verification_time': verification_time
                }
            else:
                return {
                    'verified': False,
                    'counterexample': None,
                    'reason': 'Solver could not determine (unknown)',
                    'verification_time': verification_time
                }
                
        except Exception as e:
            print(f"DEBUG: Verification error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'verified': False,
                'counterexample': None,
                'reason': f'Verification error: {str(e)}',
                'verification_time': time.time() - start_time
            }
    
    def _extract_counterexample(self, model, z3_vars: Dict) -> Dict:
        """Extract meaningful counterexamples from Z3 model with actual values"""
        counterexample = {}
        for var_name, z3_var in z3_vars.items():
            try:
                if z3_var in model:
                    if z3.is_int(z3_var) or z3.is_real(z3_var):
                        val = model[z3_var]
                        if z3.is_int_value(val):
                            counterexample[var_name] = val.as_long()
                        elif z3.is_real_value(val):
                            counterexample[var_name] = float(val.as_decimal(3))
                        else:
                            counterexample[var_name] = str(val)
                    elif z3.is_bool(z3_var):
                        counterexample[var_name] = bool(model[z3_var])
                    elif z3.is_string(z3_var):
                        counterexample[var_name] = str(model[z3_var])
                    else:
                        counterexample[var_name] = str(model[z3_var])
                else:
                    # Provide defaults if variable not in model
                    if z3.is_int(z3_var) or z3.is_real(z3_var):
                        if "altitude" in var_name or "alt" in var_name:
                            counterexample[var_name] = 35.0  
                        elif "speed" in var_name:
                            counterexample[var_name] = 15.0  
                        elif "distance" in var_name:
                            counterexample[var_name] = 15.0  
                        elif "voltage" in var_name:
                            counterexample[var_name] = 10.0 
                        else:
                            counterexample[var_name] = 0.0
                    elif z3.is_bool(z3_var):
                        if "is_holding" in var_name:
                            counterexample[var_name] = True  
                        else:
                            counterexample[var_name] = False
                    elif z3.is_string(z3_var):
                        if "action" in var_name:
                            counterexample[var_name] = "Grasp" 
                        else:
                            counterexample[var_name] = "test"
            except Exception as e:
                print(f"DEBUG: Error extracting {var_name}: {e}")
                if "voltage" in var_name:
                    counterexample[var_name] = 10.0
                else:
                    counterexample[var_name] = "unknown"
        
        return counterexample


class NeuroSymbolicVerifier:
    """
    Enhanced Neuro-Symbolic Verifier with all components from the document
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.formal_verifier = FormalVerifier()
        self.metrics = {
            'total_iterations': 0,
            'successful_verifications': 0,
            'failed_verifications': 0,
            'total_verification_time': 0.0
        }
    
    def run_generate_test_critique_refine(self, specification, max_iterations=5, initial_requirement=None):
        """Enhanced refinement loop with formal verification"""
        
        requirement = initial_requirement or specification.requirement
        iterations = []
        
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")
            
            if iteration == 0:
                prompt = self._create_initial_prompt(requirement, specification)
            else:
                prompt = self._create_feedback_prompt(requirement, iterations[-1])
            
            generated_code = self.llm_client.generate_code(prompt)
            print(f"Generated Code:\n{generated_code}")
            
            verification_result = self.formal_verifier.verify_safety_property(
                generated_code, 
                specification.formal_property,
                specification.variables
            )

            self.metrics['total_iterations'] += 1
            self.metrics['total_verification_time'] += verification_result['verification_time']
            
            iteration_result = {
                'iteration': iteration + 1,
                'generated_code': generated_code,
                'verification_result': verification_result,
                'prompt_used': prompt
            }
            iterations.append(iteration_result)
            
            print(f"Verification: {verification_result['reason']}")
            print(f"Time: {verification_result['verification_time']:.3f}s")
            
            if verification_result['verified']:
                self.metrics['successful_verifications'] += 1
                break
            else:
                self.metrics['failed_verifications'] += 1
                if verification_result['counterexample']:
                    print(f"Counterexample: {verification_result['counterexample']}")
        
        final_verification_passed = iterations[-1]['verification_result']['verified']
        final_counterexample = iterations[-1]['verification_result'].get('counterexample')
        
        return {
            'specification_id': specification.id,
            'iterations': len(iterations),
            'verification_passed': final_verification_passed,
            'iteration_details': iterations,
            'final_code': iterations[-1]['generated_code'],
            'final_counterexample': final_counterexample,
            'metrics': self.metrics.copy(),
        }
    
    def _create_initial_prompt(self, requirement, specification):
        """Create prompt that STRONGLY enforces direct implementation"""
        var_list = list(specification.variables.keys())
        var_types = {k: v for k, v in specification.variables.items()}
        
        return f"""Generate a Python verification function for this autonomous system requirement:

REQUIREMENT: {requirement}

SAFETY PROPERTY (MUST BE PRESERVED): {specification.formal_property}

REQUIRED FUNCTION SIGNATURE:
def verify_property({', '.join(var_list)}):
    # Your implementation here
    return <boolean expression>

VARIABLE TYPES:
{chr(10).join([f"  {var}: {typ}" for var, typ in var_types.items()])}

CRITICAL RULES:
1. Use EXACTLY these variable names: {', '.join(var_list)}
2. Implement the logic DIRECTLY in the return statement
3. NO intermediate variables like 'antecedent', 'consequent', etc.
4. The function must return a boolean expression

Example for Implies(A, B):
CORRECT: return not A or B
WRONG: 
antecedent = A
consequent = B
return not antecedent or consequent

Return ONLY the Python function code:"""

    def _create_feedback_prompt(self, requirement, previous_iteration):
        """Create feedback prompt that prevents requirement changes"""
        verification = previous_iteration['verification_result']
        counterexample = verification.get('counterexample', {})
        
        counterexample_text = "\n".join([f"{k} = {v}" for k, v in counterexample.items()])
        
        return f"""The previous code failed formal verification. Here is the specific logical flaw:

ORIGINAL REQUIREMENT: {requirement}

PREVIOUS CODE:
{previous_iteration['generated_code']}

VERIFICATION RESULT: {verification['reason']}

COUNTEREXAMPLE (violating scenario):
{counterexample_text}

CRITICAL: Do NOT change the original requirement or safety property. The problem is in the IMPLEMENTATION logic, not the requirements.

Generate corrected Python code that:
1. Maintains the EXACT same requirement and safety property
2. Fixes the logical error that allows the counterexample scenario
3. Uses the same function signature and variables
4. Returns only boolean (True/False) verification

Return ONLY the corrected Python function code:"""

    def print_statistics(self):
        print("\n=== Verification Statistics ===")
        for key, value in self.metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.3f}")
            else:
                print(f"{key}: {value}")