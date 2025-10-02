# main.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import RealLLMClient
from safety_specification import create_safety_specifications

def main():
    """Main demonstration of the neuro-symbolic verification framework"""
    print("Neuro-Symbolic Code Verification Framework")
    print("Based on: 'Neuro-Symbolic Framework for Verifying Logical Consistency'")
    print("=" * 60)

    llm_client = RealLLMClient()
    verifier = NeuroSymbolicVerifier(llm_client)
    specifications = create_safety_specifications()
    results = []
    for spec in specifications[:2]: 
        result = verifier.run_generate_test_critique_refine(spec, max_iterations=3)
        results.append(result)
    
  
    print("\n" + "="*60)
    print("VERIFICATION RESULTS SUMMARY")
    print("="*60)
    
    for result in results:
        status = "PASS" if result["verification_passed"] else "FAIL"
        print(f"{status} {result['specification_id']} - Iterations: {result['iterations']}")
        if not result["verification_passed"]:
            print(f"   Last counterexample: {result['final_counterexample']}")
    
   
    verifier.print_statistics()

if __name__ == "__main__":
    main()