"""
AI Service — uses Gemini 2.0 Flash to extract invoice data from WhatsApp messages.
"""

import json
import os
from app.config import ROOT_DIR
from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """You are an expert invoice assistant for FinanceFlow.
Your task is to extract invoice details from WhatsApp messages.

Required Fields:
1. Client Name (e.g., "ABC Corp")
2. Invoice Date (YYYY-MM-DD format)
3. Invoice Month (e.g., "March 2024")
4. Items: List of objects containing { description, price, quantity }

Rules:
- If a field is missing or ambiguous, you MUST identify it.
- If the message says "ABC Corp 5 laptops at 1000 each", extract Client: "ABC Corp", Item: "laptops", Qty: 5, Price: 1000.
- If the user only says "I want to create an invoice for ABC Corp for 5 laptops", ask for the price.
- Always return valid JSON only, no markdown formatting.

Output Format (JSON):
{
  "status": "complete" | "incomplete",
  "data": {
    "client_name": string | null,
    "date": string | null,
    "month": string | null,
    "items": Array<{ "description": string, "price": number, "quantity": number }>
  },
  "questions": string[]
}"""


async def extract_invoice_data(message: str) -> dict:
    """
    Send a WhatsApp message to Gemini and extract structured invoice data.
    Returns parsed JSON with status, data, and questions.
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            [
                {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                {
                    "role": "model",
                    "parts": [
                        {
                            "text": "Understood. I will extract invoice data from messages and return valid JSON."
                        }
                    ],
                },
                {"role": "user", "parts": [{"text": message}]},
            ]
        )

        # Extract JSON from the response
        text = response.text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        return json.loads(text)
    except Exception as e:
        return {
            "status": "error",
            "data": {"client_name": None, "date": None, "month": None, "items": []},
            "questions": [f"Sorry, I couldn't process your message. Error: {str(e)}"],
        }
