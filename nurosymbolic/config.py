# config.py
import os
from dotenv import load_dotenv

# Load .env file to ensure environment variables are available
load_dotenv(override=True)  # Override any existing env vars with .env values

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Llama Configuration
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama3:8b")
LLAMA_HOST = os.getenv("LLAMA_HOST", "http://localhost:11434")

# Select active LLM (options: "gemini" or "llama")
ACTIVE_LLM = os.getenv("ACTIVE_LLM", "gemini")

# Verification Settings
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 5))
VERIFICATION_TIMEOUT = int(os.getenv("VERIFICATION_TIMEOUT", 30))  # seconds

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SAFETY_SPECS = [
    {
        "id": "drone_altitude",
        "requirement": "The drone must maintain an altitude between 40 meters and 60 meters inclusive.",
        "formal_property": "And(altitude >= 40, altitude <= 60)",
        "variables": {"altitude": "real"}
    },
    {
        "id": "robotic_grasp", 
        "requirement": "The robotic arm must never perform a Grasp action if the object is already held.",
        "formal_property": "Implies(action == StringVal('Grasp'), Not(is_holding))",
        "variables": {"is_holding": "bool", "action": "string"}
    }
]