# config.py
import os


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")


MAX_ITERATIONS = 5
VERIFICATION_TIMEOUT = 30  # seconds


LOG_LEVEL = "INFO"


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