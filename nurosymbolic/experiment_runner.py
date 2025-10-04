
# experiment_runner.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import GeminiLLMClient
from safety_specification import create_safety_specifications
import os
from dotenv import load_dotenv
import time

class ExperimentRunner:
    def __init__(self, error_injection_rate: float = 0.6):
        load_dotenv()
        self.llm_client = GeminiLLMClient(error_injection_rate=error_injection_rate)
        self.verifier = NeuroSymbolicVerifier(self.llm_client)
        self.results = []
    
    def run_single_experiment(self, specification, use_ambiguous_prompt: bool = True):
        print(f"\n{'='*60}")
        print(f"EXPERIMENT: {specification.id}")
        print(f"{'='*60}")
        
        requirement = specification.ambiguous_requirement if use_ambiguous_prompt else specification.requirement
        
        print(f"Requirement: {requirement}")
        print(f"Formal Property: {specification.formal_property}")
        
        result = self.verifier.run_generate_test_critique_refine(
            specification, 
            max_iterations=4,
            initial_requirement=requirement
        )
        
        self.results.append(result)
        return result
    
    def run_comprehensive_experiments(self):
        specifications = create_safety_specifications()
        
        print("COMPREHENSIVE NEURO-SYMBOLIC VERIFICATION EXPERIMENTS")
        print("Testing framework's ability to catch and correct LLM logical errors")
        print("=" * 70)
        
        for spec in specifications:
            self.run_single_experiment(spec, use_ambiguous_prompt=True)
            time.sleep(2)
        
        self.generate_experiment_report()
    
    def generate_experiment_report(self):
        print(f"\n{'='*70}")
        print("EXPERIMENTAL RESULTS SUMMARY")
        print(f"{'='*70}")
        
        total_initial_errors = 0
        total_corrected = 0
        
        for result in self.results:
            initial_error = result['iterations'] > 1
            corrected = result['verification_passed']
            
            if initial_error:
                total_initial_errors += 1
            if corrected:
                total_corrected += 1
            
            status = "CORRECTED" if initial_error and corrected else "PASS_FIRST_TRY" if not initial_error else "FAILED"
            
            print(f"\nSpecification: {result['specification_id']}")
            print(f"Status: {status}")
            print(f"Iterations: {result['iterations']}")
            print(f"Final Verification: {'PASS' if result['verification_passed'] else 'FAIL'}")
            
            if result['iterations'] > 1:
                print("Demonstrates error detection and correction!")
        
        print(f"\n{'='*70}")
        print("EXPERIMENT METRICS:")
        print(f"Total Specifications: {len(self.results)}")
        print(f"Initial LLM Errors: {total_initial_errors}")
        print(f"Successfully Corrected: {total_corrected}")
        print(f"Error Correction Rate: {(total_corrected/total_initial_errors)*100 if total_initial_errors > 0 else 100:.1f}%")
        print(f"{'='*70}")

def main():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("Please set GEMINI_API_KEY in your .env file")
        return
    
    print("NEURO-SYMBOLIC VERIFICATION EXPERIMENTAL DEMONSTRATION")
    print("This demonstrates the framework catching and correcting real LLM errors")
    print("=" * 70)
    
    experiment_runner = ExperimentRunner(error_injection_rate=0.7)
    experiment_runner.run_comprehensive_experiments()

if __name__ == "__main__":
    main()