
import os
from google import genai
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("GEMINI_API_KEY")

print(f"Testing key: {api_key[:10]}...{api_key[-5:]}")

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Hello, this is a test.",
    )
    print("SUCCESS: Key is working!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"FAILURE: Key is not working.")
    print(f"Error: {e}")
