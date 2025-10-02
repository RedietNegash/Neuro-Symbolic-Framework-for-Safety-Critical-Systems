# main.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import GeminiLLMClient
from safety_specification import create_safety_specifications
import os

def setup_environment():
    """Setup environment and validate API key"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print(" Please set your GEMINI_API_KEY environment variable")
        print("   You can get one from: https://aistudio.google.com/app/apikey")
        print("   Then run: export GEMINI_API_KEY='your-api-key'")
        return False
    return True

def main():
    """Main demonstration of the neuro-symbolic verification framework with Gemini"""
    print("Neuro-Symbolic Code Verification Framework")
    print("Using Google Gemini as LLM backend")
    print("=" * 60)
    

    if not setup_environment():
        return
    
    try:

        llm_client = GeminiLLMClient()
        

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
            print(f"   Final code:\n{result['final_code']}\n")
        
        verifier.print_statistics()
        
    except Exception as e:
        print(f"Error running verification framework: {e}")
        print("Make sure you have a valid Gemini API key and internet connection")

if __name__ == "__main__":
    main()