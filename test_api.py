import os
from google import genai
from dotenv import load_dotenv  # ⬅️ Import load_dotenv

# 1. Load the environment variables from the .env file
load_dotenv() 

# 2. These two lines are now obsolete and can be removed or commented out:
# GEMINI_API_KEY="AIzaSyCnQB4U0fnQiWVrJ76KKcDMXGslhD4CKHc"
# GEMINI_MODEL="gemini-3-pro-preview"

def test_gemini_api():
    # Load from environment variables (this is where load_dotenv() is effective)
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
    
    # ... rest of your original code ...

    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY is not set.")
        return

    try:
        # Client initialization remains the same
        client = genai.Client(api_key=api_key) 

        response = client.models.generate_content(
            model=model_name,
            contents="Explain how AI works in a few words."
        )

        print("✅ API WORKING!")
        print("🔹 Model Used:", model_name)
        print("🔹 Response:")
        print(response.text)

    except Exception as e:
        print("❌ API TEST FAILED")
        print("Error:", e)


if __name__ == "__main__":
    test_gemini_api()