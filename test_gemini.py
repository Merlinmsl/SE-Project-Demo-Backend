from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Testing gemini-1.5-flash...")
try:
    resp = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Hello, say 'Test successful'."
    )
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
