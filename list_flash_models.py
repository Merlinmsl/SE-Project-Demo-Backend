from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Flash models:")
try:
    for model in client.models.list():
        if "flash" in model.name:
            print(model.name)
except Exception as e:
    print(f"Error listing models: {e}")
