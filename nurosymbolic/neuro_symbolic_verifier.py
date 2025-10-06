# neuro_symbolic_verifier.py
from typing import Dict, List, Optional, Any
from z3 import *
import time
from symbolic_bridge import ASTToZ3Translator

class FormalVerifier:
    """
    Formal Verification Component using SMT Solver
    As described in Section 2.4 of the document
    """
    
    def __init__(self):
        self.solver = z3.Solver()
        self.translator = ASTToZ3Translator()
    
    def verify_safety_property(self, python_code: str, safety_property: str, 
                             specification_vars: Dict) -> Dict[str, Any]:
        """
        Formal verification as described in Section 2.4
        Returns: Dict with verification results and counterexample if violation exists
        """
        start_time = time.time()
        
        try:
            # Step 1: Parse Python code to Z3 using symbolic bridge
            code_z3_expr = self.translator.python_code_to_z3(python_code)
            
            # Step 2: Create Z3 variables from specification
            z3_vars = {}
            for var_name, var_type in specification_vars.items():
                if var_type == "int":
                    z3_vars[var_name] = Int(var_name)
                elif var_type == "real":
                    z3_vars[var_name] = Real(var_name)
                elif var_type == "bool":
                    z3_vars[var_name] = Bool(var_name)
                elif var_type == "string":
                    z3_vars[var_name] = String(var_name)
            
            # Step 3: Convert safety property string to Z3 expression
            safety_z3 = eval(safety_property, globals(), z3_vars)
            
            # Step 4: Assert NEGATION of safety property (critical step)
            negated_safety = z3.Not(safety_z3)
            
            # Step 5: Reset solver and add constraints
            self.solver.reset()
            self.solver.add(code_z3_expr)
            self.solver.add(negated_safety)
            
            # Step 6: Check satisfiability
            result = self.solver.check()
            
            verification_time = time.time() - start_time
            
            # Step 7: Interpret results
            if result == z3.unsat:
                return {
                    'verified': True,
                    'counterexample': None,
                    'reason': 'Property always holds',
                    'verification_time': verification_time
                }
            elif result == z3.sat:
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
            return {
                'verified': False,
                'counterexample': None,
                'reason': f'Verification error: {str(e)}',
                'verification_time': time.time() - start_time
            }
    
    def _extract_counterexample(self, model, z3_vars: Dict) -> Dict:
        """Extract human-readable counterexample from Z3 model"""
        counterexample = {}
        for var_name, z3_var in z3_vars.items():
            try:
                if z3.is_int_value(z3_var) or z3.is_real_value(z3_var):
                    counterexample[var_name] = model[z3_var].as_decimal(2)
                elif z3.is_bool(z3_var):
                    counterexample[var_name] = model[z3_var]
                elif z3.is_string(z3_var):
                    counterexample[var_name] = model[z3_var]
            except:
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
            
            # Step 1: Generate code using LLM
            if iteration == 0:
                prompt = self._create_initial_prompt(requirement, specification)
            else:
                prompt = self._create_feedback_prompt(requirement, iterations[-1])
            
            generated_code = self.llm_client.generate_code(prompt)
            print(f"Generated Code:\n{generated_code}")
            
            # Step 2: Formal Verification
            verification_result = self.formal_verifier.verify_safety_property(
                generated_code, 
                specification.formal_property,
                specification.variables
            )
            
            # Update metrics
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
        
        return {
            'specification_id': specification.id,
            'iterations': len(iterations),
            'verification_passed': final_verification_passed,
            'iteration_details': iterations,
            'final_code': iterations[-1]['generated_code'],
            'metrics': self.metrics.copy()
        }
    
    def _create_initial_prompt(self, requirement, specification):
        """Create structured initial prompt as described in Section 2.2"""
        return f"""You are an expert autonomous system control logic developer. Generate Python code that implements the following requirement:

REQUIREMENT: {requirement}

SAFETY CONSTRAINTS (NON-NEGOTIABLE):
- The code must satisfy: {specification.formal_property}
- Variables: {specification.variables}

Generate clean, correct Python code that implements this requirement while strictly adhering to all safety constraints. Return only the Python code without explanations."""

    def _create_feedback_prompt(self, requirement, previous_iteration):
        """Create feedback prompt with counterexample as described in Section 2.5"""
        verification = previous_iteration['verification_result']
        counterexample = verification.get('counterexample', {})
        
        counterexample_text = "\n".join([f"- {k} = {v}" for k, v in counterexample.items()])
        
        return f"""Previous code failed formal verification. Here's the specific issue:

REQUIREMENT: {requirement}

PREVIOUS CODE:
{previous_iteration['generated_code']}

VERIFICATION FAILURE:
{verification['reason']}

COUNTEREXAMPLE (violating scenario):
{counterexample_text}

Generate corrected Python code that fixes this specific logical flaw. Ensure the new code handles the counterexample scenario correctly while still satisfying the original requirement. Return only the Python code without explanations."""