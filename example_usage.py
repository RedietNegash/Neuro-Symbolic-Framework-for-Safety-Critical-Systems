from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import GeminiLLMClient
from llm_client_llama import LlamaLLMClient
from safety_specification import SafetySpecification
import os
import config

def example_single_verification():
    """Example of verifying a single safety specification with selected LLM"""
    
    #select Active LLM Gemini or LlaMA
    if config.ACTIVE_LLM.lower() == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("Please set GEMINI_API_KEY environment variable for Gemini")
        return
    
    
    llm_client = GeminiLLMClient() if config.ACTIVE_LLM.lower() == "gemini" else LlamaLLMClient()
    verifier = NeuroSymbolicVerifier(llm_client)
    
    
    spec = SafetySpecification(
        id="custom_altitude_check",
        requirement="The drone must maintain altitude between 40 and 60 meters, but never go below 40 or above 60.",
        formal_property="And(altitude >= 40, altitude <= 60)",
        variables={"altitude": "real"}
    )
    
    print(f"Testing single specification with {config.ACTIVE_LLM.capitalize()}...")
    result = verifier.run_generate_test_critique_refine(spec, max_iterations=3)
    
    print(f"\nResult: {'PASS' if result['verification_passed'] else 'FAIL'}")
    print(f"Iterations: {result['iterations']}")
    if result['final_counterexample']:
        print(f"Counterexample: {result['final_counterexample']}")
    print(f"Final code:\n{result['final_code']}")

def example_batch_verification():
    """Example of batch verification with multiple specifications"""
    
    if config.ACTIVE_LLM.lower() == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("Please set GEMINI_API_KEY environment variable for Gemini")
        return
    
    llm_client = GeminiLLMClient() if config.ACTIVE_LLM.lower() == "gemini" else LlamaLLMClient()
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
    
    print(f"Batch verification with {config.ACTIVE_LLM.capitalize()}...")
    for spec in specifications:
        result = verifier.run_generate_test_critique_refine(spec, max_iterations=2)
        status = "passed" if result["verification_passed"] else "failed"
        print(f"{status} {spec.id}: {result['iterations']} iterations")

if __name__ == "__main__":
    example_single_verification()
    print("\n" + "="*50)
    example_batch_verification()