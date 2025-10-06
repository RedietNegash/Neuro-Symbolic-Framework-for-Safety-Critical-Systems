# experiment_runner.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier, FormalVerifier
from llm_client import GeminiLLMClient
from safety_specification import create_safety_specifications, DatasetGenerator, BugInjector
import os
from dotenv import load_dotenv
import time
import statistics
from typing import Dict, List

class BaselineComparisons:
    """
    Implements baseline comparisons as described in Section 3.3
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.formal_verifier = FormalVerifier()
    
    def llm_only_baseline(self, specification, use_ambiguous_prompt=True):
        """LLM-only baseline: Single pass generation without verification"""
        requirement = specification.ambiguous_requirement if use_ambiguous_prompt else specification.requirement
        
        prompt = f"Generate Python code for: {requirement}. Return only code."
        generated_code = self.llm_client.generate_code(prompt)
        
        # Verify the result
        verification = self.formal_verifier.verify_safety_property(
            generated_code, specification.formal_property, specification.variables
        )
        
        return {
            'specification_id': specification.id,
            'generated_code': generated_code,
            'verified': verification['verified'],
            'iterations': 1,
            'verification_time': verification['verification_time']
        }
    
    def llm_unit_test_baseline(self, specification, max_iterations=5, use_ambiguous_prompt=True):
        """LLM + Unit Tests baseline: Iterative refinement based on test failures"""
        requirement = specification.ambiguous_requirement if use_ambiguous_prompt else specification.requirement
        
        iterations = []
        generated_code = ""
        
        for iteration in range(max_iterations):
            if iteration == 0:
                prompt = f"Generate Python code for: {requirement}. Return only code."
            else:
                # Simulate unit test feedback
                test_failures = self._simulate_unit_test_failures(generated_code, specification)
                prompt = f"""Previous code failed tests. Fix these issues:

REQUIREMENT: {requirement}

FAILING TESTS:
{test_failures}

Generate corrected Python code. Return only code."""
            
            generated_code = self.llm_client.generate_code(prompt)
            
            # Verify with formal method for fair comparison
            verification = self.formal_verifier.verify_safety_property(
                generated_code, specification.formal_property, specification.variables
            )
            
            iterations.append({
                'iteration': iteration + 1,
                'verified': verification['verified'],
                'verification_time': verification['verification_time']
            })
            
            if verification['verified']:
                break
        
        return {
            'specification_id': specification.id,
            'iterations': len(iterations),
            'verified': iterations[-1]['verified'],
            'total_verification_time': sum(i['verification_time'] for i in iterations),
            'iteration_details': iterations
        }
    
    def _simulate_unit_test_failures(self, code: str, specification) -> str:
        """Simulate unit test failures - simpler than formal verification"""
        # This is a simplified simulation for the baseline
        failures = []
        
        if "altitude" in code:
            if ">= 40" not in code and "> 40" not in code:
                failures.append("Fails when altitude = 39")
            if "<= 60" not in code and "< 60" not in code:
                failures.append("Fails when altitude = 61")
        
        if "speed" in code and "distance" in code:
            if "distance < 20" in code and "speed <= 10" not in code:
                failures.append("Fails when distance=15, speed=12")
        
        return "\n".join(failures) if failures else "All tests passed (but may have logical errors)"

class EvaluationMetrics:
    """
    Comprehensive evaluation metrics as described in Section 3.1
    """
    
    def __init__(self):
        self.metrics = {
            'logical_consistency_rate': 0.0,
            'test_case_pass_rate': 0.0,
            'error_reduction_percentage': 0.0,
            'refinement_iterations': [],
            'computational_overhead': [],
            'baseline_comparisons': {}
        }
    
    def calculate_metrics(self, neuro_symbolic_results, baseline_results, initial_error_count):
        """Calculate all metrics from Section 3.1"""
        
        # Logical Consistency Rate
        successful_verifications = sum(1 for r in neuro_symbolic_results if r['verification_passed'])
        self.metrics['logical_consistency_rate'] = successful_verifications / len(neuro_symbolic_results)
        
        # Refinement Iterations
        self.metrics['refinement_iterations'] = [r['iterations'] for r in neuro_symbolic_results]
        
        # Computational Overhead
        verification_times = []
        for result in neuro_symbolic_results:
            for iteration in result.get('iteration_details', []):
                verification_times.append(iteration['verification_result']['verification_time'])
        self.metrics['computational_overhead'] = verification_times
        
        # Error Reduction Percentage
        final_error_count = len(neuro_symbolic_results) - successful_verifications
        if initial_error_count > 0:
            self.metrics['error_reduction_percentage'] = (
                (initial_error_count - final_error_count) / initial_error_count * 100
            )
        
        # Baseline Comparisons
        self.metrics['baseline_comparisons'] = baseline_results
    
    def generate_report(self):
        """Generate comprehensive evaluation report"""
        report = []
        report.append("COMPREHENSIVE EVALUATION METRICS")
        report.append("=" * 50)
        
        report.append(f"Logical Consistency Rate: {self.metrics['logical_consistency_rate']:.1%}")
        report.append(f"Error Reduction Percentage: {self.metrics['error_reduction_percentage']:.1f}%")
        
        if self.metrics['refinement_iterations']:
            avg_iterations = statistics.mean(self.metrics['refinement_iterations'])
            report.append(f"Mean Refinement Iterations: {avg_iterations:.2f}")
        
        if self.metrics['computational_overhead']:
            avg_time = statistics.mean(self.metrics['computational_overhead'])
            report.append(f"Average Verification Time: {avg_time:.3f}s")
        
        # Baseline comparisons
        if self.metrics['baseline_comparisons']:
            report.append("\nBASELINE COMPARISONS:")
            for method, results in self.metrics['baseline_comparisons'].items():
                success_rate = sum(1 for r in results if r['verified']) / len(results)
                report.append(f"{method}: {success_rate:.1%} success rate")
        
        return "\n".join(report)

class ExperimentRunner:
    def __init__(self, error_injection_rate: float = 0.6):
        load_dotenv()
        self.llm_client = GeminiLLMClient(error_injection_rate=error_injection_rate)
        self.verifier = NeuroSymbolicVerifier(self.llm_client)
        self.baselines = BaselineComparisons(self.llm_client)
        self.evaluator = EvaluationMetrics()
        self.results = {
            'neuro_symbolic': [],
            'llm_only': [],
            'llm_unit_tests': []
        }
    
    def run_single_experiment(self, specification, use_ambiguous_prompt: bool = True):
        """Run comprehensive experiment for one specification"""
        print(f"\n{'='*60}")
        print(f"EXPERIMENT: {specification.id}")
        print(f"{'='*60}")
        
        requirement = specification.ambiguous_requirement if use_ambiguous_prompt else specification.requirement
        
        print(f"Requirement: {requirement}")
        print(f"Formal Property: {specification.formal_property}")
        
        # Run Neuro-Symbolic approach
        neuro_symbolic_result = self.verifier.run_generate_test_critique_refine(
            specification, 
            max_iterations=4,
            initial_requirement=requirement
        )
        
        # Run baselines
        llm_only_result = self.baselines.llm_only_baseline(specification, use_ambiguous_prompt)
        llm_unit_tests_result = self.baselines.llm_unit_test_baseline(specification, 4, use_ambiguous_prompt)
        
        # Store results
        self.results['neuro_symbolic'].append(neuro_symbolic_result)
        self.results['llm_only'].append(llm_only_result)
        self.results['llm_unit_tests'].append(llm_unit_tests_result)
        
        return {
            'neuro_symbolic': neuro_symbolic_result,
            'llm_only': llm_only_result,
            'llm_unit_tests': llm_unit_tests_result
        }
    
    def run_comprehensive_experiments(self):
        """Run experiments on all specifications"""
        specifications = create_safety_specifications()
        
        print("COMPREHENSIVE NEURO-SYMBOLIC VERIFICATION EXPERIMENTS")
        print("Testing framework with baseline comparisons")
        print("=" * 70)
        
        # Count initial errors (from LLM-only baseline)
        initial_errors = 0
        
        for spec in specifications:
            result = self.run_single_experiment(spec, use_ambiguous_prompt=True)
            
            # Track initial errors
            if not result['llm_only']['verified']:
                initial_errors += 1
            
            time.sleep(2)  # Rate limiting
        
        # Calculate comprehensive metrics
        self.evaluator.calculate_metrics(
            self.results['neuro_symbolic'],
            {
                'LLM-only': self.results['llm_only'],
                'LLM+UnitTests': self.results['llm_unit_tests']
            },
            initial_errors
        )
        
        self.generate_comprehensive_report()
    
    def generate_comprehensive_report(self):
        """Generate detailed experimental report"""
        print(f"\n{'='*70}")
        print("COMPREHENSIVE EXPERIMENTAL RESULTS")
        print(f"{'='*70}")
        
        # Neuro-Symbolic results
        neuro_success = sum(1 for r in self.results['neuro_symbolic'] if r['verification_passed'])
        llm_only_success = sum(1 for r in self.results['llm_only'] if r['verified'])
        unit_tests_success = sum(1 for r in self.results['llm_unit_tests'] if r['verified'])
        
        total_specs = len(self.results['neuro_symbolic'])
        
        print(f"\nPERFORMANCE COMPARISON:")
        print(f"{'Method':<20} {'Success Rate':<15} {'Avg Iterations':<15}")
        print(f"{'-'*50}")
        print(f"{'Neuro-Symbolic':<20} {neuro_success}/{total_specs} ({neuro_success/total_specs:.1%})")
        print(f"{'LLM-only':<20} {llm_only_success}/{total_specs} ({llm_only_success/total_specs:.1%})")
        print(f"{'LLM+UnitTests':<20} {unit_tests_success}/{total_specs} ({unit_tests_success/total_specs:.1%})")
        
        # Detailed metrics from evaluator
        print(f"\n{self.evaluator.generate_report()}")
        
        # Show specific improvements
        improvement_over_llm = (neuro_success - llm_only_success) / total_specs * 100
        improvement_over_tests = (neuro_success - unit_tests_success) / total_specs * 100
        
        print(f"\nKEY IMPROVEMENTS:")
        print(f"Neuro-Symbolic vs LLM-only: +{improvement_over_llm:.1f}% improvement")
        print(f"Neuro-Symbolic vs LLM+UnitTests: +{improvement_over_tests:.1f}% improvement")
        
        # Show framework efficiency
        total_iterations = sum(r['iterations'] for r in self.results['neuro_symbolic'])
        avg_iterations = total_iterations / total_specs
        
        print(f"\nFRAMEWORK EFFICIENCY:")
        print(f"Average iterations to convergence: {avg_iterations:.2f}")
        print(f"Total verification time: {self.verifier.metrics['total_verification_time']:.2f}s")

def main():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("Please set GEMINI_API_KEY in your .env file")
        return
    
    print("ENHANCED NEURO-SYMBOLIC VERIFICATION FRAMEWORK")
    print("With Comprehensive Evaluation and Baseline Comparisons")
    print("=" * 70)
    
    experiment_runner = ExperimentRunner(error_injection_rate=0.7)
    experiment_runner.run_comprehensive_experiments()

if __name__ == "__main__":
    main()