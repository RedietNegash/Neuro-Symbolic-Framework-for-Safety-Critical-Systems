# example_usage.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import GeminiLLMClient
from safety_specification import SafetySpecification
import os

def example_single_verification():
    """Example of verifying a single safety specification with Gemini"""
    
    if not os.getenv("GEMINI_API_KEY"):
        print("Please set GEMINI_API_KEY environment variable")
        return
    

    llm_client = GeminiLLMClient()
    verifier = NeuroSymbolicVerifier(llm_client)
    

    spec = SafetySpecification(
        id="custom_altitude_check",
        requirement="The drone must maintain altitude between 40 and 60 meters, but never go below 40 or above 60.",
        formal_property="And(altitude >= 40, altitude <= 60)",
        variables={"altitude": "real"}
    )
    
    print("Testing single specification with Gemini...")
    result = verifier.run_generate_test_critique_refine(spec, max_iterations=3)
    
    print(f"\nResult: {'PASS' if result['verification_passed'] else 'FAIL'}")
    print(f"Iterations: {result['iterations']}")
    if result['final_counterexample']:
        print(f"Counterexample: {result['final_counterexample']}")
    print(f"Final code:\n{result['final_code']}")

def example_batch_verification():
    """Example of batch verification with multiple specifications"""
    
    if not os.getenv("GEMINI_API_KEY"):
        print("Please set GEMINI_API_KEY environment variable")
        return
    
    llm_client = GeminiLLMClient()
    verifier = NeuroSymbolicVerifier(llm_client)
    
  
    specifications = [
        SafetySpecification(
            id="speed_limit",
            requirement="The vehicle must not exceed 100 km/h speed limit.",
            formal_property="speed <= 100",
            variables={"speed": "real"}
        ),
        SafetySpecification(
            id="temperature_control",
            requirement="The system must maintain temperature between 20°C and 25°C.",
            formal_property="And(temperature >= 20, temperature <= 25)",
            variables={"temperature": "real"}
        )
    ]
    
    print(" Batch verification with Gemini...")
    for spec in specifications:
        result = verifier.run_generate_test_critique_refine(spec, max_iterations=2)
        status = "passed" if result["verification_passed"] else "failed "
        print(f"{status} {spec.id}: {result['iterations']} iterations")

if __name__ == "__main__":
    example_single_verification()
    print("\n" + "="*50)
    example_batch_verification()