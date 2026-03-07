"""
AI Service — uses Google Gen AI (Gemini 2.0 Flash) to extract invoice data.
Migrated from google-generativeai to google-genai.
"""

import json
import os
import re
import base64
from google import genai
from google.genai import types
from app.config import ROOT_DIR
from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Initialize the Gen AI Client
client = genai.Client(api_key=GEMINI_API_KEY)


def _extract_json(text: str) -> dict:
    """
    Robustly extract JSON from an AI response.
    Handles: raw JSON, ```json fences, conversational text around JSON, etc.
    """
    text = text.strip()

    # 1. Try direct parse first (ideal case)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from ```json ... ``` code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the first { ... } block anywhere in the text
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from AI response: {text[:200]}")

def get_system_prompt():
    from datetime import date
    today = date.today().isoformat()
    return f"""You are an expert AI sales and invoice assistant.
Your task is to detect order intent and extract details from WhatsApp messages.

Current Date: {today} (Use this for date and month if not mentioned)

Required Fields for an Order:
1. item_name (e.g., "Curry Puffs")
2. quantity (e.g., 5)
(Note: client_name and price are optional because they are managed by the system.)

Rules for Order Intent & Data Collection:
- Look for `item_name` ("description") and `quantity`.
- If the user wants to order something but is missing `quantity`, set status to "incomplete".
- Generate a friendly, conversational question in the `questions` array asking for the missing quantity (e.g., "I see you want to order Curry Puffs! How many would you like to get?").
- If all required info (item and quantity) is present, set status to "complete" and generate the `items` array.
- For `price` and `client_name`, return null if not explicitly provided in the text.
- Return valid JSON only, no markdown formatting.

Output Format (JSON):
{{
  "status": "complete" | "incomplete",
  "data": {{
    "client_name": string | null,
    "date": string | null,
    "month": string | null,
    "currency": "MYR",
    "items": [
      {{ "description": string, "price": number | null, "quantity": number }}
    ]
  }},
  "questions": ["friendly follow-up question here"]
}}"""


async def extract_invoice_data(message: str) -> dict:
    """
    Send a WhatsApp message to Gemini and extract structured invoice data.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                temperature=0.1,
            ),
        )

        return _extract_json(response.text)
    except Exception as e:
        return {
            "status": "error",
            "data": {"client_name": None, "date": None, "month": None, "items": []},
            "questions": [f"Sorry, I couldn't process your message. Error: {str(e)}"],
        }


async def extract_receipt_data(image_bytes: bytes, mime_type: str) -> dict:
    """
    Send a receipt image to Gemini and extract structured data.
    """
    try:
        system_prompt = """You are an expert OCR and financial data extraction AI.
Extract the following information from the receipt image or PDF:
1. transaction_date (YYYY-MM-DD format)
2. amount (numeric only, omit currency symbols)
3. currency (string, e.g., "MYR", "USD", "SGD", "IDR", "PHP", "THB" - detect RM/Ringgit as MYR, S$ as SGD, Rp as IDR, ₱ as PHP, ฿ as THB, ₫ as VND. Default to "MYR" if not found)
4. reference_number (string)
5. sender_name (string)
6. bank_name (string)

If the document has multiple pages, extract the summary/total information from the relevant page.
Return valid JSON exactly matching these keys. If a field is not found or ambiguous, return null for that field. Do not include markdown formatting.
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                system_prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )

        return _extract_json(response.text)
    except Exception as e:
        return {"error": str(e)}


async def classify_media_intent(image_bytes: bytes, mime_type: str) -> dict:
    """
    Send an image/PDF to Gemini to classify its intent:
    CUSTOMER_RECEIPT, SUPPLIER_INVOICE, or IRRELEVANT.
    Returns: {"detected_type": "...", "extracted_data": {...}}
    """
    try:
        system_prompt = """You are an expert financial document classifier.
Determine if the provided image is a:
1. CUSTOMER_RECEIPT: Proof that a customer paid us (e.g., bank transfer slip).
2. SUPPLIER_INVOICE: A bill from a supplier that we need to pay.
3. IRRELEVANT: Non-financial images.

If CUSTOMER_RECEIPT or SUPPLIER_INVOICE, extract relevant data:
For CUSTOMER_RECEIPT: amount, transaction_date, reference_number.
For SUPPLIER_INVOICE: amount, transaction_date, supplier_name, currency.

Return a JSON object:
{
  "detected_type": "CUSTOMER_RECEIPT" | "SUPPLIER_INVOICE" | "IRRELEVANT",
  "extracted_data": {
     "amount": 123.45,
     "transaction_date": "YYYY-MM-DD",
     "reference_number": "...",
     "supplier_name": "...",
     "currency": "MYR"
  } 
}
Do not include markdown formatting.
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                system_prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )

        return _extract_json(response.text)
    except Exception as e:
        return {"detected_type": "ERROR", "extracted_data": {"error": str(e)}}


async def extract_supplier_invoice_v2(image_bytes: bytes, mime_type: str) -> dict:
    """
    Extract detailed supplier invoice JSON including vendor, buyer, and line_items.
    """
    try:
        system_prompt = """You are an expert OCR and financial data extraction AI.
Extract detailed supplier invoice data from the image into a JSON object strictly matching this schema:
{
  "vendor": { "name": "string", "address": "string", "contact": "string" },
  "buyer": { "name": "string", "address": "string" },
  "transaction_date": "YYYY-MM-DD",
  "reference_number": "string",
  "currency": "string",
  "amount": 0.0,
  "line_items": [
     {
        "item_id": "string",
        "description": "string",
        "origin_country": "string",
        "unit": "string",
        "price": 0.0,
        "quantity": 0,
        "subtotal": 0.0
     }
  ]
}
Ensure all numeric fields are proper numbers.
Detect base currency accurately (e.g., MYR, USD).
Do not include markdown formatting.
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                system_prompt,
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )

        return _extract_json(response.text)
    except Exception as e:
        print(f"Extraction V2 Error: {e}")
        return {"error": str(e)}


async def evaluate_supplier_bill(
    amount: float,
    currency: str,
    description: str,
    supplier_name: str,
    cash_on_hand: float,
    available_for_expenses: float,
    base_currency: str,
    line_items: list = None,
) -> dict:
    if line_items is None:
        line_items = []
    """
    Ask Gemini if it's safe to auto-pay this supplier bill based on cash flow and propose negotiation if needed.
    """
    try:
        system_prompt = f"""You are a financial controller AI making payment decisions based on cash flow.

Invoice Details:
- Supplier Name: {supplier_name}
- Total Amount: {amount} {currency}
- Details: {description}
- Line Items: {json.dumps(line_items)}

Current Financial Health:
- Cash On Hand: {cash_on_hand} {base_currency}
- Available for Expenses: {available_for_expenses} {base_currency}

Perform a 3-way financial cross-check:
1. "Cash-on-Hand Check": Do we have enough raw cash to pay (Total Amount <= Cash on Hand)? If no, decision must be "defer".
2. "Expense-Buffer Check": Will paying this leave the "Available for expenses" >= 0 (Total Amount <= Available for Expenses)?
3. "Strategy Decision": 
   - If Both checks pass: "approve"
   - If Cash check passes but Expense-Buffer fails (Total Amount > Available for Expenses): "negotiate"
   - If neither passes: "defer"

If "negotiate":
Identify which line items to reduce in quantity to fit the {available_for_expenses} budget. Formulate a polite counter-offer directly to the supplier.

Return JSON EXACTLY matching:
{{
  "decision": "approve" | "negotiate" | "defer",
  "reason": "short explanation",
  "negotiation_message": "message to supplier or null"
}}
No markdown.
        """
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=system_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )
        return _extract_json(response.text)
    except Exception as e:
        print(f"Error evaluating bill: {e}")
        return {"decision": "defer", "reason": "Failed to invoke AI evaluation.", "negotiation_message": None}
