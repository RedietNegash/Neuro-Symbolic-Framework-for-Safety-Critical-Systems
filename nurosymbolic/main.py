# main.py
from neuro_symbolic_verifier import NeuroSymbolicVerifier
from llm_client import GeminiLLMClient
from llm_client_llama import LlamaLLMClient
from safety_specification import create_safety_specifications
import os
from dotenv import load_dotenv
import config

def setup_environment():
    """Setup environment by loading .env file"""
    load_dotenv(override=True)
    
    if config.ACTIVE_LLM.lower() == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your-gemini-api-key-here":
            print("Please set your GEMINI_API_KEY in the .env file")
            print("   You can get one from: https://aistudio.google.com/app/apikey")
            return False
        print(f"Gemini API key loaded (first 10 chars): {api_key[:10]}...")
    elif config.ACTIVE_LLM.lower() == "llama":
        try:
            import ollama
            ollama.Client(host=config.LLAMA_HOST).list()
            print(f"Llama model selected: {config.LLAMA_MODEL} at {config.LLAMA_HOST}")
        except Exception as e:
            print(f"Failed to connect to Ollama server: {e}")
            print("Ensure Ollama is running (run 'ollama serve') and the model is pulled (run 'ollama pull llama3:8b')")
            return False
    else:
        print(f"Invalid ACTIVE_LLM value: {config.ACTIVE_LLM}. Must be 'gemini' or 'llama'.")
        return False
    return True

def main():
    """Main demonstration of the neuro-symbolic verification framework with selected LLM"""
    print("Neuro-Symbolic Code Verification Framework")
    print(f"Using {config.ACTIVE_LLM.capitalize()} as LLM backend")
    print("=" * 60)
    
    if not setup_environment():
        return
    
    try:
        llm_client = GeminiLLMClient() if config.ACTIVE_LLM.lower() == "gemini" else LlamaLLMClient()
        
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
        print("Ensure Gemini API key is valid (if using Gemini) or Ollama is running (if using Llama)")

if __name__ == "__main__":
    main()