from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"Testing key: {key[:10]}...")

client = genai.Client(api_key=key)
try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello"
    )
    print("SUCCESS:", response.text)
except Exception as e:
    print("FAILED:", type(e).__name__, ":", e)
