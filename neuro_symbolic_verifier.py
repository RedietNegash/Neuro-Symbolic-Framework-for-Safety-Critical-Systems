import ast
import time
import json
from typing import Dict, List, Tuple, Optional, Any
from llm_ensemble import LLMEnsemble
from experimental_analyzer import ExperimentalAnalyzer
from safety_specification import SafetySpecification
from python_to_z3_converter import PythonToZ3Converter
from z3 import *

class NeuroSymbolicVerifier:
    """Main neuro-symbolic verification framework with individual model testing"""
    
    def __init__(self):
        self.ensemble = LLMEnsemble()
        self.analyzer = ExperimentalAnalyzer()
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
        """Generate SIMPLE initial prompt for LLM"""
        variable_names = ", ".join(specification.variables.keys())
        
        return f"""Write a Python function that checks: "{specification.requirement}"
        
Parameters: {variable_names}
Return: True if safe, False if unsafe

Write ONLY the function code, nothing else.
"""
    
    def generate_refinement_prompt(self, specification: SafetySpecification,
                                 code: str, counterexample: Dict) -> str:
        """Generate simple refinement prompt"""
        ce_description = self._format_counterexample(counterexample)
        variable_names = ", ".join(specification.variables.keys())
        
        return f"""Fix this function for: "{specification.requirement}"
        
Current code:
{code}

Error: {ce_description}

Write the corrected function with parameters: {variable_names}
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
        try:
            # Clean the code string
            code_string = self._clean_code(code_string)
            
            # Parse and verify
            tree = ast.parse(code_string)
            converter = PythonToZ3Converter(specification.z3_vars)
            converter.visit(tree)
            
            solver = Solver()
            solver.set("timeout", 10000)  # 10 second timeout
            
            for assertion in converter.assertions:
                solver.add(assertion)
            
            # Get property expression
            property_expr = eval(specification.formal_property, globals(), specification.z3_vars)
            
            # Check if code implies property
            solver.add(Not(property_expr))
            result = solver.check()
            
            if result == sat:
                model = solver.model()
                counterexample = {}
                for decl in model.decls():
                    counterexample[decl.name()] = str(model[decl])
                return False, counterexample
            elif result == unsat:
                return True, None
            else:
                return False, {"error": "Z3 timeout or unknown"}
                
        except Exception as e:
            print(f"Verification error: {e}")
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
        
        return '\n'.join(lines)
    
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
                print(f"    ✓ VERIFICATION PASSED")
                break
            else:
                print(f"    ✗ VERIFICATION FAILED - Counterexample: {counterexample}")
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
        """Extract Python code from LLM response"""
        if not text:
            return ""
        
        import re
        
        # Look for code blocks first
        patterns = [
            r'```python\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                extracted = matches[0].strip()
                if extracted and 'def ' in extracted:
                    return extracted
        
        # If no code block, look for function definition
        lines = text.split('\n')
        function_start = -1
        function_lines = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                function_start = i
                function_lines.append(line)
                break
        
        if function_start >= 0:
            # Get the rest of the function
            for i in range(function_start + 1, len(lines)):
                current_line = lines[i]
                # Stop if we hit another def
                if current_line.strip().startswith('def '):
                    break
                function_lines.append(current_line)
            
            return '\n'.join(function_lines).strip()
        
        return text.strip()
    
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
            current_code = self.ensemble.arbitrate(candidates)
            
            if not current_code:
                print("    No valid code generated")
                break
            
            # Verify
            verification_passed, counterexample = self.verify_code(current_code, specification)
            
            if verification_passed:
                print(f"    ✓ PASSED")
                break
            else:
                print(f"    ✗ FAILED - Counterexample: {counterexample}")
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
        print("\n📊 INDIVIDUAL MODEL PERFORMANCE:")
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
        print("\n🎯 ENSEMBLE PERFORMANCE:")
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
        print("\n📋 DETAILED COMPARISON PER SPECIFICATION:")
        print("-" * 80)
        
        for spec_result in self.verification_stats.get("detailed_results", []):
            print(f"\n🔹 {spec_result['specification_id']}")
            print(f"   Requirement: {spec_result['requirement']}")
            print(f"   {'='*40}")
            
            # Individual model results
            print(f"   INDIVIDUAL MODELS:")
            for model_name, model_result in spec_result.get('individual_model_results', {}).items():
                status = "✓ PASS" if model_result.get('verification_passed') else "✗ FAIL"
                iterations = model_result.get('iterations', 0)
                print(f"     {model_name.upper():<10} {status:<8} Iterations: {iterations}")
                if model_result.get('final_code'):
                    code_preview = model_result['final_code'][:60].replace('\n', ' ') + ('...' if len(model_result['final_code']) > 60 else '')
                    print(f"               Code: {code_preview}")
            
            # Ensemble result
            print(f"\n   ENSEMBLE APPROACH:")
            ensemble_result = spec_result.get('ensemble_result', {})
            status = "✓ PASS" if ensemble_result.get('verification_passed') else "✗ FAIL"
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
        print("\n📈 OVERALL COMPARISON TABLE:")
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
        filename = f"model_comparison_report_{timestamp}.json"
        
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
            print(f"\n⚠️ Could not save comparison report: {e}")
    
    def print_detailed_report(self):
        """Print detailed report for all models and specifications"""
        print("\n" + "="*80)
        print("DETAILED PERFORMANCE REPORT")
        print("="*80)
        
        # 1. Overall Statistics
        print("\n📊 OVERALL VERIFICATION STATISTICS:")
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
        print("\n🤖 MODEL PERFORMANCE COMPARISON:")
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