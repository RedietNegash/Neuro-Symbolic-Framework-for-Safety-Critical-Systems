# neuro_symbolic_verifier.py
from typing import Dict, List, Tuple, Optional, Any
from llm_client import RealLLMClient
from safety_specification import SafetySpecification
from python_to_z3_converter import PythonToZ3Converter
from z3 import *

class NeuroSymbolicVerifier:
    """Main neuro-symbolic verification framework"""
    
    def __init__(self, llm_client: RealLLMClient):
        self.llm = llm_client
        self.verification_stats = {
            "total_verifications": 0,
            "successful_verifications": 0,
            "failed_verifications": 0,
            "average_iterations": 0,
            "total_iterations": 0
        }
    
    def generate_initial_prompt(self, specification: SafetySpecification) -> str:
        """Generate initial prompt for LLM"""
        return f"""
        SAFETY-CRITICAL CODE GENERATION TASK
        
        REQUIREMENT: {specification.requirement}
        
        Please generate a Python function that implements this requirement exactly.
        The function should return True when the safety condition is satisfied and False otherwise.
        
        Important safety constraints:
        - The code must be logically correct and handle all edge cases
        - Use clear variable names and simple logic
        - Focus on the core safety property
        
        Generate only the Python function code without any explanations.
        """
    
    def generate_refinement_prompt(self, specification: SafetySpecification, 
                                 code: str, counterexample: Dict) -> str:
        """Generate refinement prompt with counterexample feedback"""
        ce_description = self._format_counterexample(counterexample)
        
        return f"""
        CODE REFINEMENT TASK
        
        ORIGINAL REQUIREMENT: {specification.requirement}
        
        PREVIOUS CODE (has logical error):
        ```python
        {code}
        ```
        
        VERIFICATION FAILED: The code violates the safety property.
        
        COUNTEREXAMPLE: {ce_description}
        
        Please fix the code to handle this case correctly while still satisfying the original requirement.
        Generate only the corrected Python function code without any explanations.
        """
    
    def _format_counterexample(self, counterexample: Dict) -> str:
        """Format counterexample for natural language feedback"""
        parts = []
        for var, value in counterexample.items():
            parts.append(f"{var} = {value}")
        return "; ".join(parts)
    
    def parse_python_code(self, code_string: str) -> str:
        """Extract Python code from LLM response"""
        if "```python" in code_string:
            start = code_string.find("```python") + 9
            end = code_string.find("```", start)
            code_string = code_string[start:end].strip()
        elif "```" in code_string:
            start = code_string.find("```") + 3
            end = code_string.find("```", start)
            code_string = code_string[start:end].strip()
        
        return code_string
    
    def verify_code(self, code_string: str, specification: SafetySpecification) -> Tuple[bool, Optional[Dict]]:
        """Verify code against formal specification using Z3"""
        try:
          
            tree = ast.parse(code_string)
              
            converter = PythonToZ3Converter(specification.z3_vars)
            converter.visit(tree)
       
            solver = Solver()
            for assertion in converter.assertions:
                solver.add(assertion)
            
        
            property_expr = eval(specification.formal_property, globals(), specification.z3_vars)
            solver.add(Not(property_expr))
            
           
            result = solver.check()
            
            if result == sat:
                model = solver.model()
                counterexample = {}
                for decl in model.decls():
                    counterexample[decl.name()] = str(model[decl])
                return False, counterexample
            else:
                return True, None
                
        except Exception as e:
            print(f"Verification error: {e}")
            return False, {"error": str(e)}
    
    def run_generate_test_critique_refine(self, specification: SafetySpecification, 
                                        max_iterations: int = 5) -> Dict:
        """Run the full neuro-symbolic verification cycle"""
        print(f"\n Starting verification for: {specification.id}")
        print(f"Requirement: {specification.requirement}")
        
        iterations = 0
        current_code = None
        verification_passed = False
        final_counterexample = None
        
        for iteration in range(max_iterations):
            iterations += 1
            print(f"\n Iteration {iteration}")
            

            if iteration == 0:
                prompt = self.generate_initial_prompt(specification)
                print("Generating initial code...")
            else:
                prompt = self.generate_refinement_prompt(specification, current_code, final_counterexample)
                print("Refining code with counterexample feedback...")
            
           
            llm_response = self.llm.generate_code(prompt)
            current_code = self.parse_python_code(llm_response)
            print(f"Generated code:\n{current_code}")
            
            
            print("🔎 Verifying code with formal methods...")
            verification_passed, counterexample = self.verify_code(current_code, specification)
            
            if verification_passed:
                print("Verification PASSED - Code is logically consistent!")
                break
            else:
                print(f"Verification FAILED - Counterexample: {counterexample}")
                final_counterexample = counterexample
        
      
        self._update_stats(verification_passed, iterations)
        
        return {
            "specification_id": specification.id,
            "verification_passed": verification_passed,
            "iterations": iterations,
            "final_code": current_code,
            "final_counterexample": final_counterexample if not verification_passed else None
        }
    
    def _update_stats(self, passed: bool, iterations: int):
        """Update verification statistics"""
        self.verification_stats["total_verifications"] += 1
        self.verification_stats["total_iterations"] += iterations
        
        if passed:
            self.verification_stats["successful_verifications"] += 1
        else:
            self.verification_stats["failed_verifications"] += 1
        
        self.verification_stats["average_iterations"] = (
            self.verification_stats["total_iterations"] / 
            self.verification_stats["total_verifications"]
        )
    
    def print_statistics(self):
        """Print verification statistics"""
        print("\n" + "="*50)
        print("NEURO-SYMBOLIC VERIFICATION STATISTICS")
        print("="*50)
        stats = self.verification_stats
        print(f"Total Verifications: {stats['total_verifications']}")
        print(f"Successful: {stats['successful_verifications']}")
        print(f"Failed: {stats['failed_verifications']}")
        print(f"Success Rate: {(stats['successful_verifications']/stats['total_verifications'])*100:.1f}%")
        print(f"Average Iterations: {stats['average_iterations']:.1f}")