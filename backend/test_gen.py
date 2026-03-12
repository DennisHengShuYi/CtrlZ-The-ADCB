import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models_to_try = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-2.5-flash"
]

for m in models_to_try:
    try:
        print(f"Trying model: {m}")
        response = client.models.generate_content(
            model=m,
            contents="Say hello"
        )
        print(f"Success with {m}: {response.text}")
        break
    except Exception as e:
        print(f"Failed with {m}: {e}")
