# example_usage.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import RealLLMClient
from safety_specification import SafetySpecification

def example_with_local_llm():
    """Example using a local LLM (e.g., Ollama)"""
    
   
    local_llm_client = RealLLMClient(
        base_url="http://localhost:11434/v1",
        api_key="ollama",  
        model="codellama:7b" 
    )


    verifier = NeuroSymbolicVerifier(local_llm_client)

  
    spec = SafetySpecification(
        id="test_altitude",
        requirement="The drone must maintain altitude between 40 and 60 meters.",
        formal_property="And(altitude >= 40, altitude <= 60)", 
        variables={"altitude": "real"}
    )


    result = verifier.run_generate_test_critique_refine(spec)
    print("Result:", result)

if __name__ == "__main__":
    example_with_local_llm()