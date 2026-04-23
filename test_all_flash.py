from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models_to_try = [
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.0-pro"
]

for model in models_to_try:
    print(f"Testing {model}...")
    try:
        resp = client.models.generate_content(
            model=model,
            contents="Hello"
        )
        print(f"  Result: Success! ({resp.text[:20]}...)")
        break
    except Exception as e:
        print(f"  Result: Failed ({str(e)[:50]}...)")
