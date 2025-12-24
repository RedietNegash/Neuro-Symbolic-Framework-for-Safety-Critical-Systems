import os
from dotenv import load_dotenv

# Load .env file to ensure environment variables are available
load_dotenv()

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Llama Configuration
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama3:8b")
LLAMA_HOST = os.getenv("LLAMA_HOST", "http://localhost:11434")

# DeepSeek Configuration
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:7b")
DEEPSEEK_HOST = os.getenv("DEEPSEEK_HOST", "http://localhost:11434")

# Select active approach
# Options: "gemini", "llama", "deepseek", or "ensemble"
ACTIVE_APPROACH = os.getenv("ACTIVE_LLM", "ensemble")  # Default to ensemble

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
    },
    {
        "id": "rotation_speed_limit",
        "requirement": "The drone's rotation speed must not exceed 5 rad/s when an obstacle is detected within 0.5 meters.",
        "formal_property": "Implies(distance < 0.5, rotation_speed <= 5)",
        "variables": {"rotation_speed": "real", "distance": "real"}
    },
    {
        "id": "drone_speed_obstacle",
        "requirement": "The drone's speed must never exceed 10 m/s when an obstacle is detected within 20 meters.",
        "formal_property": "Implies(distance < 20, speed <= 10)",
        "variables": {"speed": "real", "distance": "real"}
    }
]