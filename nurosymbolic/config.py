# config.py
import os


LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "your-api-key-here")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")


MAX_ITERATIONS = 5
VERIFICATION_TIMEOUT = 30  # seconds


LOG_LEVEL = "INFO"