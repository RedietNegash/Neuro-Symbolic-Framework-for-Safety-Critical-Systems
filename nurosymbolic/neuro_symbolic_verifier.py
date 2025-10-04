# neuro_symbolic_verifier.py
import ast
from typing import Dict, List, Tuple, Optional, Any
from llm_client import GeminiLLMClient
from safety_specification import SafetySpecification
from python_to_z3_converter import PythonToZ3Converter
from z3 import *

class NeuroSymbolicVerifier:
    def __init__(self, llm_client: GeminiLLMClient):
        self.llm = llm_client
        self.verification_stats = {
            "total_verifications": 0,
            "successful_verifications": 0,
            "failed_verifications": 0,
            "average_iterations": 0,
            "total_iterations": 0,
            "errors_caught": 0,
            "errors_corrected": 0
        }
    
    def generate_initial_prompt(self, specification: SafetySpecification, ambiguous_requirement: str) -> str:
        return f"""
Generate Python code for this safety requirement:

REQUIREMENT: {ambiguous_requirement}

Create a function that returns True when the safety condition is satisfied and False otherwise.

Provide only the Python code without explanations.
"""
    def generate_refinement_prompt(self, specification: SafetySpecification, 
                                 code: str, counterexample: Dict) -> str:
        ce_description = self._format_counterexample(counterexample)
        
        return f"""
The previous code had a logical error. Here's what went wrong:
ORIGINAL REQUIREMENT: {specification.requirement}

BUGGY CODE:
```python
{code}
ERROR FOUND: The code fails when {ce_description}

Please fix the code to handle this case correctly.
Provide only the corrected Python code.
"""
    def _format_counterexample(self, counterexample: Dict) -> str:
        if 'error' in counterexample:
            return f"code parsing failed: {counterexample['error']}"
        parts = []
        for var, value in counterexample.items():
            parts.append(f"{var} = {value}")
        return "; ".join(parts)

    def parse_python_code(self, code_string: str) -> str:
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

    def run_generate_test_critique_refine(self, specification: SafetySpecification, max_iterations: int = 5, initial_requirement: str = None) -> Dict:
        requirement = initial_requirement or specification.requirement
        print(f"Starting verification for: {specification.id}")
        print(f"Requirement: {requirement}")
        iterations = 0
        current_code = None
        verification_passed = False
        final_counterexample = None
        initial_error = False
        for iteration in range(max_iterations):
            iterations += 1
            print(f"Iteration {iteration}")
            if iteration == 0:
                prompt = self.generate_initial_prompt(specification, requirement)
                print("Generating initial code")
            else:
                prompt = self.generate_refinement_prompt(specification, current_code, final_counterexample)
                print("Refining code with counterexample feedback")
            llm_response = self.llm.generate_code(prompt, specification.id, is_refinement=(iteration > 0))
            current_code = self.parse_python_code(llm_response)
            print(f"Generated code:\n{current_code}")
            print("Verifying code with formal methods")
            verification_passed, counterexample = self.verify_code(current_code, specification)
            if verification_passed:
                print("Verification PASSED - Code is logically consistent")
                if iteration > 0:
                    self.verification_stats["errors_corrected"] += 1
                break
            else:
                print(f"Verification FAILED - Counterexample: {counterexample}")
                final_counterexample = counterexample
                if iteration == 0:
                    initial_error = True
                    self.verification_stats["errors_caught"] += 1
        self._update_stats(verification_passed, iterations)
        return {
            "specification_id": specification.id,
            "verification_passed": verification_passed,
            "iterations": iterations,
            "final_code": current_code,
            "final_counterexample": final_counterexample if not verification_passed else None,
            "initial_error": initial_error
        }

    def _update_stats(self, passed: bool, iterations: int):
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
        print("\n" + "="*50)
        print("NEURO-SYMBOLIC VERIFICATION STATISTICS")
        print("="*50)
        stats = self.verification_stats
        print(f"Total Verifications: {stats['total_verifications']}")
        print(f"Successful: {stats['successful_verifications']}")
        print(f"Failed: {stats['failed_verifications']}")
        success_rate = (stats['successful_verifications']/stats['total_verifications'])*100
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Average Iterations: {stats['average_iterations']:.1f}")
        print(f"Errors Caught: {stats['errors_caught']}")
        print(f"Errors Corrected: {stats['errors_corrected']}")
        parts = []
        for var, value in counterexample.items():
            parts.append(f"{var} = {value}")
        return "; ".join(parts)

    def parse_python_code(self, code_string: str) -> str:
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
        try:
            print("DEBUG_VERIFIER: Starting verification process")
            print(f"DEBUG_VERIFIER: Code to verify:\n{code_string}")
            
            tree = ast.parse(code_string)
            print("DEBUG_VERIFIER: Successfully parsed AST")
            
            code_safety_var = Bool('code_safety_judgment')
            extended_z3_vars = specification.z3_vars.copy()
            extended_z3_vars['function_return'] = code_safety_var  
            
            print(f"DEBUG_VERIFIER: Z3 variables: {extended_z3_vars}")
            
            converter = PythonToZ3Converter(extended_z3_vars)
            converter.visit(tree)
            
            print(f"DEBUG_VERIFIER: Converter created {len(converter.assertions)} assertions")
            for i, assertion in enumerate(converter.assertions):
                print(f"DEBUG_VERIFIER: Assertion {i}: {assertion}")
            
            solver = Solver()
            for assertion in converter.assertions:
                solver.add(assertion)
            

            property_expr = eval(specification.formal_property, globals(), specification.z3_vars)
            print(f"DEBUG_VERIFIER: Safety property: {property_expr}")
            
            verification_condition = (code_safety_var != property_expr)
            solver.add(verification_condition)
            print(f"DEBUG_VERIFIER: Looking for cases where: {verification_condition}")
            
            result = solver.check()
            print(f"DEBUG_VERIFIER: Solver result: {result}")
            
            if result == sat:
                model = solver.model()
                print(f"DEBUG_VERIFIER: Model found: {model}")
                counterexample = {}
                for decl in model.decls():
                    if decl.name() not in ['function_return', '__code_output__']:
                        counterexample[decl.name()] = str(model[decl])
                print(f"DEBUG_VERIFIER: Counterexample: {counterexample}")
                return False, counterexample
            else:
                print("DEBUG_VERIFIER: No counterexample found - code is correct")
                return True, None
                
        except Exception as e:
            print(f"DEBUG_VERIFIER: Verification error: {e}")
            return False, {"error": str(e)}

    def run_generate_test_critique_refine(self, specification: SafetySpecification, max_iterations: int = 5, initial_requirement: str = None) -> Dict:
        requirement = initial_requirement or specification.requirement
        print(f"Starting verification for: {specification.id}")
        print(f"Requirement: {requirement}")
        iterations = 0
        current_code = None
        verification_passed = False
        final_counterexample = None
        initial_error = False
        for iteration in range(max_iterations):
            iterations += 1
            print(f"Iteration {iteration}")
            if iteration == 0:
                prompt = self.generate_initial_prompt(specification, requirement)
                print("Generating initial code")
            else:
                prompt = self.generate_refinement_prompt(specification, current_code, final_counterexample)
                print("Refining code with counterexample feedback")
            llm_response = self.llm.generate_code(prompt, specification.id, is_refinement=(iteration > 0))
            current_code = self.parse_python_code(llm_response)
            print(f"Generated code:\n{current_code}")
            print("Verifying code with formal methods")
            verification_passed, counterexample = self.verify_code(current_code, specification)
            if verification_passed:
                print("Verification PASSED - Code is logically consistent")
                if iteration > 0:
                    self.verification_stats["errors_corrected"] += 1
                break
            else:
                print(f"Verification FAILED - Counterexample: {counterexample}")
                final_counterexample = counterexample
                if iteration == 0:
                    initial_error = True
                    self.verification_stats["errors_caught"] += 1
        self._update_stats(verification_passed, iterations)
        return {
            "specification_id": specification.id,
            "verification_passed": verification_passed,
            "iterations": iterations,
            "final_code": current_code,
            "final_counterexample": final_counterexample if not verification_passed else None,
            "initial_error": initial_error
        }

    def _update_stats(self, passed: bool, iterations: int):
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
        print("\n" + "="*50)
        print("NEURO-SYMBOLIC VERIFICATION STATISTICS")
        print("="*50)
        stats = self.verification_stats
        print(f"Total Verifications: {stats['total_verifications']}")
        print(f"Successful: {stats['successful_verifications']}")
        print(f"Failed: {stats['failed_verifications']}")
        success_rate = (stats['successful_verifications']/stats['total_verifications'])*100
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Average Iterations: {stats['average_iterations']:.1f}")
        print(f"Errors Caught: {stats['errors_caught']}")
        print(f"Errors Corrected: {stats['errors_corrected']}")