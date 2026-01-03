import ast
import time
import json
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from src.models.llm_ensemble import LLMEnsemble
from src.core.experimental_analyzer import ExperimentalAnalyzer
from src.verification.safety_specification import SafetySpecification
from src.verification.python_to_z3_converter import PythonToZ3Converter
from src.verification.loop_invariant_synthesizer import LoopInvariantSynthesizer
from z3 import *


class FormalVerifier:
    """Formal Verification Component using Z3, aligned with user's snippet behavior."""

    def __init__(self):
        self.solver = Solver()

    def verify_safety_property(self, python_code: str, specification: SafetySpecification) -> Dict[str, Any]:
        start_time = time.time()
        try:
            # Parse and convert Python code to Z3 assertions
            tree = ast.parse(python_code)
            converter = PythonToZ3Converter(specification.z3_vars)
            converter.visit(tree)

            code_assertions = getattr(converter, 'assertions', []) or []
            if code_assertions:
                code_expr = And(*code_assertions)
            else:
                code_expr = BoolVal(True)

            # Prepare z3 vars mapping
            if getattr(specification, 'z3_vars', None):
                z3_vars = specification.z3_vars.copy()
            else:
                z3_vars = {}
                for var_name, var_type in getattr(specification, 'variables', {}).items():
                    if var_type in ('int', 'I', 'Int'):
                        z3_vars[var_name] = Int(var_name)
                    elif var_type in ('float', 'real', 'Real'):
                        z3_vars[var_name] = Real(var_name)
                    elif var_type in ('bool', 'Bool'):
                        z3_vars[var_name] = Bool(var_name)
                    else:
                        # fallback to Int
                        z3_vars[var_name] = Int(var_name)

            # Evaluate safety property expression
            safety_z3 = eval(specification.formal_property, globals(), z3_vars)

            implication = Implies(code_expr, safety_z3)
            negated_implication = Not(implication)

            self.solver.reset()
            self.solver.set('timeout', 10000)
            self.solver.add(negated_implication)

            result = self.solver.check()
            verification_time = time.time() - start_time

            if result == sat:
                model = self.solver.model()
                counterexample = {}
                for decl in model.decls():
                    try:
                        val = model[decl]
                        # best-effort type extraction
                        if is_int_value(val):
                            counterexample[decl.name()] = val.as_long()
                        elif is_rational_value(val):
                            try:
                                counterexample[decl.name()] = float(val.as_decimal(10))
                            except Exception:
                                counterexample[decl.name()] = str(val)
                        else:
                            counterexample[decl.name()] = str(val)
                    except Exception:
                        counterexample[decl.name()] = str(model[decl])

                return {
                    'verified': False,
                    'counterexample': counterexample,
                    'reason': 'Property violation found',
                    'verification_time': verification_time
                }
            elif result == unsat:
                return {
                    'verified': True,
                    'counterexample': None,
                    'reason': 'Property always holds',
                    'verification_time': verification_time
                }
            else:
                return {
                    'verified': False,
                    'counterexample': None,
                    'reason': 'Solver unknown or timeout',
                    'verification_time': verification_time
                }

        except Exception as e:
            return {
                'verified': False,
                'counterexample': None,
                'reason': f'Verification error: {e}',
                'verification_time': time.time() - start_time
            }


class NeuroSymbolicVerifier:
    """Main neuro-symbolic verification framework with individual model testing"""
    
    def __init__(self):
        self.ensemble = LLMEnsemble()
        self.analyzer = ExperimentalAnalyzer()
        self.invariant_synthesizer = LoopInvariantSynthesizer()
        self.formal_verifier = FormalVerifier()
        self.verification_stats = {
            "total_verifications": 0,
            "successful_verifications": 0,
            "failed_verifications": 0,
            "average_iterations": 0,
            "total_iterations": 0,
            "individual_model_results": {},  # Track each model's individual results
            "ensemble_results": {},  # Track ensemble results
            "detailed_results": []  # Store detailed results for each spec
        }
    
    def generate_initial_prompt(self, specification: SafetySpecification) -> str:
        """Generate STRICT initial prompt for LLM to ensure verifiable code"""
        variable_names = ", ".join(specification.variables.keys())
        
        return f"""Write a Python function that checks: "{specification.requirement}"
        
STRICT GUIDELINES:
1. Function name: anything relevant (e.g., check_safety)
2. Parameters: EXACTLY {variable_names}
3. Return: True if safe, False if unsafe
4. USE ONLY simple boolean logic and comparisons.
6. FORBIDDEN:
   - NO type checking (type(), isinstance())
   - NO dictionary/list access (e.g., data['x'])
   - NO complex Python features (match/case, decorators)
   - NO extra print statements or conversational text
   - NO use of 'None' (Python NoneType). Use strings like 'None' or booleans instead.
7. Output: Provide ONLY the Python code inside a code block.

Parameters to use: {variable_names}
"""

    def generate_refinement_prompt(self, specification: SafetySpecification,
                                 code: str, counterexample: Dict) -> str:
        """Generate strict refinement prompt with detailed feedback"""
        ce_description = self._format_counterexample(counterexample)
        variable_names = ", ".join(specification.variables.keys())
        
        return f"""Fix this Python function for: "{specification.requirement}"
        
The previous code failed verification.
Error/Counterexample: {ce_description}

Previous code:
```python
{code}
```

STRICT GUIDELINES FOR FIX:
1. Use EXACTLY these parameters: {variable_names}
2. Fix the logic to handle the counterexample provided.
3. USE ONLY simple boolean logic and arithmetic.
4. FORBIDDEN:
   - NO type checking (e.g., don't use type() or isinstance())
   - NO complex data structures
   - NO use of 'None' (Python NoneType). Use strings like 'None' or booleans instead.
   - NO conversational filler
5. Output: Provide ONLY the corrected Python code inside a code block.
"""
    
    def _format_counterexample(self, counterexample: Dict) -> str:
        """Format counterexample for natural language feedback"""
        if "error" in counterexample:
            return f"Error: {counterexample['error']}"
        
        parts = []
        for var, value in counterexample.items():
            parts.append(f"{var} = {value}")
        
        return f"Failed for inputs: {', '.join(parts)}"
    
    def verify_code(self, code_string: str, specification: SafetySpecification) -> Tuple[bool, Optional[Dict]]:
        """Verify code against formal specification using Z3"""
        # Delegate to FormalVerifier for consistent behavior
        try:
            cleaned = self._clean_code(code_string)
            result = self.formal_verifier.verify_safety_property(cleaned, specification)
            if result.get('verified'):
                return True, None
            else:
                return False, result.get('counterexample') or {"error": result.get('reason')}
        except Exception as e:
            return False, {"error": str(e)}
    
    def _clean_code(self, code_string: str) -> str:
        """Clean LLM-generated code"""
        # Remove markdown code blocks
        if "```python" in code_string:
            start = code_string.find("```python") + 9
            end = code_string.find("```", start)
            code_string = code_string[start:end].strip()
        elif "```" in code_string:
            start = code_string.find("```") + 3
            end = code_string.find("```", start)
            code_string = code_string[start:end].strip()
        
        # Remove function type hints to simplify parsing
        lines = []
        for line in code_string.split('\n'):
            if ': bool' in line:
                line = line.replace(': bool', '')
            if ': float' in line:
                line = line.replace(': float', '')
            if ': int' in line:
                line = line.replace(': int', '')
            if ': str' in line:
                line = line.replace(': str', '')
            lines.append(line)
        cleaned = '\n'.join(lines)

        # Normalize indentation and remove accidental leading/trailing blank lines
        try:
            cleaned = textwrap.dedent(cleaned)
        except Exception:
            pass

        # Remove any leading/trailing whitespace lines
        cleaned = '\n'.join([l.rstrip() for l in cleaned.split('\n')]).strip('\n')

        return cleaned

    def _save_generated_code(self, spec_id: str, model_name: str, code: str, approach: str = "individual", iteration: Optional[int] = None) -> None:
        """Save generated Python code to disk organized by specification and approach.

        Files are written to `data/generated_code/{spec_id}/{approach}/{model_name}_iter{n}.py`.
        """
        try:
            if not code:
                return

            base_dir = Path("data") / "generated_code" / str(spec_id) / approach
            base_dir.mkdir(parents=True, exist_ok=True)

            safe_name = str(model_name).replace(" ", "_").replace("/", "_")
            safe_spec = str(spec_id).replace(" ", "_").replace("/", "_")
            if iteration is None:
                filename = base_dir / f"{safe_spec}__{safe_name}.py"
            else:
                filename = base_dir / f"{safe_spec}__{safe_name}_iter{iteration}.py"

            # Prefer to save a cleaned version to avoid AST parsing errors later
            try:
                code_to_write = self._clean_code(code)
            except Exception:
                code_to_write = code

            with open(filename, "w") as f:
                f.write(code_to_write)

            print(f"    Saved generated code: {filename}")
        except Exception as e:
            print(f"    [Warning] Could not save generated code for {model_name}: {e}")
    
    async def test_individual_model(self, model_name: str, specification: SafetySpecification, 
                                   prompt: str, max_iterations: int = 3) -> Dict:
        """Test a single model independently (no ensemble)"""
        print(f"\n  [INDIVIDUAL MODEL TEST: {model_name.upper()}]")
        
        model_client = self.ensemble.clients.get(model_name)
        if not model_client:
            print(f"    Model {model_name} not found")
            return {"model": model_name, "success": False, "error": "Model not found"}
        
        iterations = 0
        current_code = None
        verification_passed = False
        final_counterexample = None
        iteration_details = []
        
        for iteration in range(max_iterations):
            print(f"    Iteration {iteration + 1}")
            
            if iteration == 0:
                current_prompt = prompt
            else:
                current_prompt = self.generate_refinement_prompt(specification, current_code, final_counterexample)
            
            # Generate code with this specific model
            try:
                code = model_client.generate_code(current_prompt)
            except Exception as e:
                print(f"    Generation error: {e}")
                code = None
            
            if not code:
                print(f"    No code generated")
                break
            
            # Clean and store code
            current_code = self._extract_python_code(code)
            if not current_code:
                print(f"    No valid Python code extracted")
                break
            
            # Save generated code for this model + iteration
            try:
                self._save_generated_code(specification.id, model_name, current_code, approach="individual", iteration=iteration+1)
            except Exception:
                pass
            print(f"    Generated: {current_code[:80]}{'...' if len(current_code) > 80 else ''}")
            
            # Verify
            verification_passed, counterexample = self.verify_code(current_code, specification)
            
            iteration_details.append({
                "iteration": iteration + 1,
                "code": current_code[:200] + "..." if len(current_code) > 200 else current_code,
                "verification_passed": verification_passed,
                "counterexample": counterexample
            })
            
            if verification_passed:
                print(f"    [PASS] VERIFICATION PASSED")
                break
            else:
                print(f"    [FAIL] VERIFICATION FAILED - Counterexample: {counterexample}")
                final_counterexample = counterexample
        
        result = {
            "model": model_name,
            "verification_passed": verification_passed,
            "iterations": iteration + 1 if iteration_details else 0,
            "final_code": current_code,
            "final_counterexample": final_counterexample,
            "iteration_details": iteration_details
        }
        
        return result
    
    def _extract_python_code(self, text: str) -> str:
        """Extract Python code from LLM response with high resilience"""
        if not text:
            return ""
        
        # 1. Strip thinking tags if they leaked through
        raw_text = text
        if "<think>" in raw_text:
            if "</think>" in raw_text:
                raw_text = raw_text.split("</think>")[-1].strip()
            else:
                raw_text = raw_text.split("<think>")[-1].strip()

        import re
        
        # 2. Look for explicit code blocks (priority)
        patterns = [
            r'```python\s*(def\s+.*?)\s*```',
            r'```python\s*(.*?)\s*```',
            r'```\s*(def\s+.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, raw_text, re.DOTALL)
            if matches:
                candidate = matches[0].strip()
                if 'def ' in candidate:
                    # Sanity check: Ensure it's not just a conversational fragment
                    if candidate.count('(') > 0 and 'return' in candidate:
                        # Attempt to fix trailing unclosed parenthesis
                        if candidate.count('(') > candidate.count(')') and candidate.endswith('('):
                            candidate = candidate[:-1].strip()
                        return candidate
        
        # 3. Look for function definition directly in text
        lines = raw_text.split('\n')
        function_start = -1
        function_lines = []
        
        for i, line in enumerate(lines):
            # Must start with optional whitespace + def
            if re.match(r'^\s*def\s+', line):
                function_start = i
                function_lines.append(line)
                break
        
        if function_start >= 0:
            for i in range(function_start + 1, len(lines)):
                current_line = lines[i]
                # Stop if we hit a very obvious non-code line or markdown marker
                if current_line.strip().startswith('###') or current_line.strip().startswith('```'):
                    break
                # If we hit another 'def' at the start of a line, we've found another function
                if re.match(r'^def\s+', current_line):
                    break
                function_lines.append(current_line)
            
            candidate = '\n'.join(function_lines).strip()
            if 'def ' in candidate and 'return' in candidate:
                # Basic balance fix
                if candidate.count('(') > candidate.count(')'):
                    if not candidate.endswith(')'):
                        candidate += ')'
                return candidate
        
        # 4. Filter garbage: If the text contains lots of natural language and no clear code structure,
        # it might be the cause of "unterminated string literal" errors if treated as code.
        # Check if it looks like a function
        if 'def ' in raw_text and 'return' in raw_text and '(' in raw_text:
            return raw_text.strip()
            
        # If it doesn't look like code, return empty so iteration/fallback can handle it
        return ""
    
    async def run_comparison_experiment(self, specification: SafetySpecification,
                                       max_iterations: int = 3) -> Dict:
        """Run comparison experiment: test each model individually AND ensemble"""
        print(f"\n[COMPARISON EXPERIMENT] {specification.id}: {specification.requirement}")
        
        spec_details = {
            "specification_id": specification.id,
            "requirement": specification.requirement,
            "individual_model_results": {},
            "ensemble_result": None,
            "comparison_summary": {}
        }
        
        # Generate initial prompt
        prompt = self.generate_initial_prompt(specification)
        
        # Test each model individually
        individual_results = {}
        for model_name in self.ensemble.clients.keys():
            result = await self.test_individual_model(model_name, specification, prompt, max_iterations)
            individual_results[model_name] = result
        
        # Test ensemble approach
        print(f"\n  [ENSEMBLE APPROACH TEST]")
        ensemble_result = await self.run_generate_test_critique_refine(specification, max_iterations)
        
        # Store results
        spec_details["individual_model_results"] = individual_results
        spec_details["ensemble_result"] = ensemble_result
        
        # Calculate comparison summary
        successful_models = []
        for model_name, result in individual_results.items():
            if result.get("verification_passed"):
                successful_models.append(model_name)
        
        spec_details["comparison_summary"] = {
            "successful_models": successful_models,
            "total_models_tested": len(individual_results),
            "ensemble_successful": ensemble_result.get("verification_passed", False),
            "best_model": successful_models[0] if successful_models else None,
            "all_models_same": len(successful_models) == len(individual_results)
        }
        
        # Update statistics
        self.verification_stats["total_verifications"] += 1
        self.verification_stats["total_iterations"] += ensemble_result.get("total_iterations", 1)
        
        if ensemble_result.get("verification_passed"):
            self.verification_stats["successful_verifications"] += 1
        else:
            self.verification_stats["failed_verifications"] += 1
        
        # Store individual model results in stats
        for model_name, result in individual_results.items():
            if model_name not in self.verification_stats["individual_model_results"]:
                self.verification_stats["individual_model_results"][model_name] = {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "total_iterations": 0
                }
            
            model_stats = self.verification_stats["individual_model_results"][model_name]
            model_stats["total_tests"] += 1
            model_stats["total_iterations"] += result.get("iterations", 0)
            if result.get("verification_passed"):
                model_stats["successful_tests"] += 1
        
        # Store ensemble results
        if specification.id not in self.verification_stats["ensemble_results"]:
            self.verification_stats["ensemble_results"][specification.id] = []
        
        self.verification_stats["ensemble_results"][specification.id].append(ensemble_result)
        
        # Calculate average iterations
        if self.verification_stats["total_verifications"] > 0:
            self.verification_stats["average_iterations"] = (
                self.verification_stats["total_iterations"] /
                self.verification_stats["total_verifications"]
            )
        
        # Add to detailed results
        self.verification_stats["detailed_results"].append(spec_details)
        
        return spec_details
    
    async def run_generate_test_critique_refine(self, specification: SafetySpecification,
                                              max_iterations: int = 3) -> Dict:
        """Run the neuro-symbolic verification cycle with ensemble"""
        print(f"\n  [ENSEMBLE VERIFICATION]")
        
        iterations = 0
        current_code = None
        verification_passed = False
        final_counterexample = None
        
        for iteration in range(max_iterations):
            iterations = iteration + 1
            print(f"    Iteration {iterations}")
            
            if iteration == 0:
                prompt = self.generate_initial_prompt(specification)
            else:
                prompt = self.generate_refinement_prompt(specification, current_code, final_counterexample)
            
            # Generate code with ensemble
            candidates = await self.ensemble.generate_ensemble(prompt)

            # Save each candidate returned by models
            try:
                for name, cand_code in candidates.items():
                    try:
                        self._save_generated_code(specification.id, name, cand_code, approach="candidate", iteration=iterations)
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Use Z3 PRe-Check in arbitration
            current_code = self.ensemble.arbitrate(
                candidates,
                verifier_callback=self.verify_code,
                specification=specification
            )
            
            if not current_code:
                print("    No valid code generated")
                break

            # Save the arbitrated ensemble code
            try:
                self._save_generated_code(specification.id, 'ensemble', current_code, approach='ensemble', iteration=iterations)
            except Exception:
                pass
            
            # Verify
            verification_passed, counterexample = self.verify_code(current_code, specification)
            
            if verification_passed:
                print(f"    [PASS] PASSED")
                break
            else:
                print(f"    [FAIL] FAILED - Counterexample: {counterexample}")
                final_counterexample = counterexample
        
        result = {
            "specification_id": specification.id,
            "verification_passed": verification_passed,
            "total_iterations": iterations,
            "final_code": current_code,
            "final_counterexample": final_counterexample
        }
        
        return result
    
    def print_comparison_report(self):
        """Print detailed comparison report between individual models and ensemble"""
        print("\n" + "="*80)
        print("MODEL COMPARISON REPORT: INDIVIDUAL MODELS vs ENSEMBLE")
        print("="*80)
        
        # 1. Individual Model Performance Summary
        print("\n[Results] INDIVIDUAL MODEL PERFORMANCE:")
        print("-" * 60)
        print(f"{'Model':<12} {'Success Rate':<15} {'Avg Iterations':<15} {'Total Tests':<12}")
        print("-" * 60)
        
        individual_stats = self.verification_stats.get("individual_model_results", {})
        for model_name, stats in individual_stats.items():
            if stats["total_tests"] > 0:
                success_rate = (stats["successful_tests"] / stats["total_tests"]) * 100
                avg_iterations = stats["total_iterations"] / stats["total_tests"]
                print(f"{model_name:<12} {success_rate:>13.1f}% {avg_iterations:>14.2f} {stats['total_tests']:>12}")
        
        # 2. Ensemble Performance Summary
        print("\n[Done] ENSEMBLE PERFORMANCE:")
        print("-" * 60)
        print(f"{'Success Rate':<15} {'Avg Iterations':<15} {'Total Tests':<12}")
        print("-" * 60)
        
        total_specs = self.verification_stats["total_verifications"]
        successful = self.verification_stats["successful_verifications"]
        avg_iter = self.verification_stats["average_iterations"]
        
        if total_specs > 0:
            ensemble_success_rate = (successful / total_specs) * 100
            print(f"{ensemble_success_rate:>13.1f}% {avg_iter:>14.2f} {total_specs:>12}")
        
        # 3. Detailed Comparison Per Specification
        print("\n[Tasks] DETAILED COMPARISON PER SPECIFICATION:")
        print("-" * 80)
        
        for spec_result in self.verification_stats.get("detailed_results", []):
            print(f"\n[Spec] {spec_result['specification_id']}")
            print(f"   Requirement: {spec_result['requirement']}")
            print(f"   {'='*40}")
            
            # Individual model results
            print(f"   INDIVIDUAL MODELS:")
            for model_name, model_result in spec_result.get('individual_model_results', {}).items():
                status = "[PASS]" if model_result.get('verification_passed') else "[FAIL]"
                iterations = model_result.get('iterations', 0)
                print(f"     {model_name.upper():<10} {status:<8} Iterations: {iterations}")
                if model_result.get('final_code'):
                    code_preview = model_result['final_code'][:60].replace('\n', ' ') + ('...' if len(model_result['final_code']) > 60 else '')
                    print(f"               Code: {code_preview}")
            
            # Ensemble result
            print(f"\n   ENSEMBLE APPROACH:")
            ensemble_result = spec_result.get('ensemble_result', {})
            status = "[PASS]" if ensemble_result.get('verification_passed') else "[FAIL]"
            iterations = ensemble_result.get('total_iterations', 0)
            print(f"     Status: {status:<8} Iterations: {iterations}")
            if ensemble_result.get('final_code'):
                code_preview = ensemble_result['final_code'][:60].replace('\n', ' ') + ('...' if len(ensemble_result['final_code']) > 60 else '')
                print(f"     Code: {code_preview}")
            
            # Comparison summary
            summary = spec_result.get('comparison_summary', {})
            successful_models = summary.get('successful_models', [])
            print(f"\n   COMPARISON: {len(successful_models)}/{summary.get('total_models_tested', 0)} models passed")
            if successful_models:
                print(f"   Best model(s): {', '.join(successful_models)}")
        
        # 4. Overall Comparison Table
        print("\n[Results] OVERALL COMPARISON TABLE:")
        print("-" * 60)
        print(f"{'Approach':<15} {'Success Rate':<15} {'Avg Iterations':<15} {'Speedup':<12}")
        print("-" * 60)
        
        # Calculate ensemble vs individual comparison
        if individual_stats:
            best_individual = None
            best_rate = 0
            
            for model_name, stats in individual_stats.items():
                if stats["total_tests"] > 0:
                    rate = (stats["successful_tests"] / stats["total_tests"]) * 100
                    if rate > best_rate:
                        best_rate = rate
                        best_individual = model_name
            
            if best_individual:
                best_stats = individual_stats[best_individual]
                best_avg_iter = best_stats["total_iterations"] / best_stats["total_tests"]
                
                print(f"Best Individual: {best_individual:<8} {best_rate:>13.1f}% {best_avg_iter:>14.2f} {'1.00x':>12}")
                
                if total_specs > 0:
                    ensemble_rate = (successful / total_specs) * 100
                    speedup = best_avg_iter / avg_iter if avg_iter > 0 else 1.0
                    improvement = ensemble_rate - best_rate
                    
                    print(f"Ensemble: {'':<7} {ensemble_rate:>13.1f}% {avg_iter:>14.2f} {speedup:>11.2f}x")
                    print(f"Improvement: {'+'+str(round(improvement,1))+'%' if improvement > 0 else str(round(improvement,1))+'%':<14}")
        
        # 5. Save comparison report
        self._save_comparison_report()
    
    def _save_comparison_report(self):
        """Save comparison report to JSON file"""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/model_comparison_report_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "verification_stats": self.verification_stats,
            "specifications_tested": len(self.verification_stats.get("detailed_results", [])),
            "models_tested": list(self.verification_stats.get("individual_model_results", {}).keys())
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            print(f"\n📄 Comparison report saved to: {filename}")
        except Exception as e:
            print(f"\n[Warning] Could not save comparison report: {e}")
    
    def print_detailed_report(self):
        """Print detailed report for all models and specifications"""
        print("\n" + "="*80)
        print("DETAILED PERFORMANCE REPORT")
        print("="*80)
        
        # 1. Overall Statistics
        print("\n[Results] OVERALL VERIFICATION STATISTICS:")
        print("-" * 40)
        stats = self.verification_stats
        print(f"Total Specifications: {stats['total_verifications']}")
        print(f"Successfully Verified: {stats['successful_verifications']}")
        print(f"Failed: {stats['failed_verifications']}")
        
        if stats['total_verifications'] > 0:
            success_rate = (stats['successful_verifications'] / stats['total_verifications']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"Average Iterations: {stats['average_iterations']:.2f}")
        
        # 2. Model Performance Comparison
        print("\n[Models] MODEL PERFORMANCE COMPARISON:")
        print("-" * 40)
        print(f"{'Model':<12} {'Success Rate':<15} {'Avg Iterations':<15} {'Total':<8}")
        print("-" * 40)
        
        for model_name, perf in stats.get("individual_model_results", {}).items():
            if perf["total_tests"] > 0:
                success_rate = (perf["successful_tests"] / perf["total_tests"]) * 100
                avg_iterations = perf["total_iterations"] / perf["total_tests"]
                print(f"{model_name:<12} {success_rate:>13.1f}% {avg_iterations:>14.2f} {perf['total_tests']:<8}")
    
    def print_statistics(self):
        """Print verification statistics"""
        print("\n" + "="*50)
        print("VERIFICATION RESULTS SUMMARY")
        print("="*50)
        
        stats = self.verification_stats
        print(f"Total Specifications: {stats['total_verifications']}")
        print(f"Successfully Verified: {stats['successful_verifications']}")
        print(f"Failed: {stats['failed_verifications']}")
        
        if stats['total_verifications'] > 0:
            success_rate = (stats['successful_verifications'] / stats['total_verifications']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        else:
            print(f"Success Rate: 0.0%")
            
        print(f"Average Iterations: {stats['average_iterations']:.2f}")