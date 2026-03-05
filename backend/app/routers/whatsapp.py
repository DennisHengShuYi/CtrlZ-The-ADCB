import os
import json
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from google import genai

# ──────────────────────────────────────────────────────────────
# Shared environment & Gemini setup
# ──────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ WhatsApp: Gemini client initialized")
    except Exception as e:
        print(f"❌ WhatsApp: Failed to initialize Gemini client: {e}")
        client = None
else:
    print("⚠️ WhatsApp: No Gemini API key found, using fallback only")
    client = None

# Import shared Supabase client
from app.supabase_client import supabase

USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
if USE_SUPABASE:
    try:
        supabase.table("whatsapp_messages").select("*").limit(1).execute()
        print("✅ WhatsApp: Supabase connected")
    except Exception as e:
        print(f"❌ WhatsApp: Supabase connection failed: {e}")
        supabase = None
else:
    supabase = None

from app.auth import require_auth

# ──────────────────────────────────────────────────────────────
# Helper: retrieve product information from Instagram posts
# (duplicated for simplicity; in a real app you might factor this out)
# ──────────────────────────────────────────────────────────────
def get_product_info_from_posts(keywords: Optional[List[str]] = None) -> str:
    if not USE_SUPABASE or not supabase:
        return ""
    try:
        response = supabase.table("instagram_posts").select("caption").execute()
        posts = response.data
        if not posts:
            return ""
        if keywords:
            relevant = []
            for post in posts:
                caption = post["caption"].lower()
                if any(kw.lower() in caption for kw in keywords):
                    relevant.append(f"- {post['caption']}")
            if relevant:
                return "Relevant product info from Instagram:\n" + "\n".join(relevant)
            return ""
        else:
            all_captions = "\n".join([f"- {p['caption']}" for p in posts])
            return f"Our products (from Instagram):\n{all_captions}"
    except Exception as e:
        print(f"Error fetching product info: {e}")
        return ""

# ──────────────────────────────────────────────────────────────
# PILLAR 1 – CONVERSATIONAL AI (your router)
# ──────────────────────────────────────────────────────────────
pillar1_router = APIRouter(prefix="/api/whatsapp-pillar1", tags=["whatsapp-pillar1"])

class Pillar1Message(BaseModel):
    from_number: str
    text: str
    timestamp: Optional[str] = None

class Pillar1Reply(BaseModel):
    intent: str
    mood: str
    reply: str

def get_conversation_history(session_id: str, limit: int = 10) -> List[dict]:
    if not USE_SUPABASE or not supabase:
        return []
    try:
        response = supabase.table("whatsapp_messages") \
            .select("role, content, intent, mood") \
            .eq("session_id", session_id) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Failed to fetch history: {e}")
        return []

def store_message(session_id: str, role: str, content: str, intent: str = None, mood: str = None):
    if not USE_SUPABASE or not supabase:
        return
    try:
        supabase.table("whatsapp_messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "intent": intent,
            "mood": mood
        }).execute()
    except Exception as e:
        print(f"Failed to store message: {e}")

def fallback_classify(text: str) -> dict:
    text_lower = text.lower()
    if any(word in text_lower for word in ["order", "buy", "want", "how to order"]):
        intent = "order"
    elif any(word in text_lower for word in ["pay", "paid", "payment", "transfer"]):
        intent = "payment"
    else:
        intent = "interest"
    if any(word in text_lower for word in ["thank", "great", "love", "sedap", "best"]):
        mood = "happy"
    elif any(word in text_lower for word in ["why", "how", "what", "when", "where"]):
        mood = "neutral"
    elif any(word in text_lower for word in ["expensive", "bad", "not good", "sad", "mahal"]):
        mood = "sad"
    else:
        mood = "neutral"
    if intent == "order":
        reply = "Great! Could you please confirm the quantity and your delivery address?"
    elif intent == "payment":
        reply = "Thank you! You can pay via DuitNow or bank transfer. I'll send you the details."
    else:
        if mood == "happy":
            reply = "We're glad you like our products! Would you like to place an order? 😊"
        elif mood == "neutral":
            reply = "Do you have any questions about our products? I'm here to help!"
        else:
            reply = "We're sorry to hear that. Could you share your feedback so we can improve?"
    return {"intent": intent, "mood": mood, "reply": reply}

def classify_with_gemini(text: str, history: List[dict]) -> dict:
    if not client:
        raise Exception("Gemini not configured")
    history_str = ""
    for msg in history:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        history_str += f"{role}: {msg['content']}\n"

    # Fetch product info to enrich context
    product_info = get_product_info_from_posts()  # get all products

    prompt = f"""
{product_info}

You are an AI assistant for a Malaysian food business selling frozen snacks like curry puffs, roti canai, and onde-onde.
Here is the conversation so far:
{history_str}
Customer: {text}

Analyze the customer's latest message and return JSON with:
- intent: one of "interest", "order", "payment"
- mood: one of "happy", "neutral", "sad"
- reply: a friendly, appropriate response (use Malaysian/English mix if suitable)

Rules:
- If intent is "order", reply should confirm order and ask for details.
- If intent is "interest" and mood is "happy", encourage them to order.
- If intent is "interest" and mood is "neutral", ask if they have questions.
- If intent is "interest" and mood is "sad", acknowledge feedback and offer assistance.
- Keep replies warm and helpful.

Return ONLY valid JSON.
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    raw = response.text.strip()
    if raw.startswith("```json"):
        raw = raw[7:-3]
    elif raw.startswith("```"):
        raw = raw[3:-3]
    return json.loads(raw)

@pillar1_router.post("/webhook", response_model=Pillar1Reply)
async def pillar1_webhook(message: Pillar1Message):
    session_id = message.from_number
    history = get_conversation_history(session_id)
    try:
        if client:
            result = classify_with_gemini(message.text, history)
        else:
            result = fallback_classify(message.text)
    except Exception as e:
        print(f"Gemini error, using fallback: {e}")
        result = fallback_classify(message.text)
    store_message(session_id, "user", message.text, result["intent"], result["mood"])
    store_message(session_id, "assistant", result["reply"])
    return result

# ──────────────────────────────────────────────────────────────
# INVOICE PROCESSING (friend's router)
# ──────────────────────────────────────────────────────────────
from app.models import WhatsAppMessage  # from friend's models
from app.ai_service import extract_invoice_data
from app.invoice_service import (
    get_company,
    get_client_by_name,
    create_invoice,
    create_pending_invoice,
    get_pending_invoice,
    delete_pending_invoice,
)

invoice_router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp-invoice"])

@invoice_router.post("/webhook")
async def invoice_webhook(
    body: WhatsAppMessage,
    claims: dict[str, Any] = Depends(require_auth),
):
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        return {
            "status": "error",
            "message": "Please set up your company profile first.",
        }
    result = await extract_invoice_data(body.message)
    if result.get("status") == "error":
        return {
            "status": "error",
            "message": result.get("questions", ["An error occurred."])[0],
        }
    if result["status"] == "incomplete":
        data = result.get("data", {})
        questions = result.get("questions", [])
        missing = [k for k, v in data.items() if v is None or v == []]
        create_pending_invoice(
            user_id=user_id,
            raw_message=body.message,
            extracted_data=data,
            missing_fields=missing,
        )
        return {
            "status": "incomplete",
            "questions": questions,
            "extracted_data": data,
        }
    # Status == "complete"
    data = result["data"]
    client = get_client_by_name(company["id"], data.get("client_name", ""))
    if not client:
        return {
            "status": "client_not_found",
            "message": f"Client '{data.get('client_name')}' not found. Would you like to create a new client?",
            "extracted_data": data,
        }
    from datetime import date as date_type
    invoice_date = data.get("date", str(date_type.today()))
    month = data.get("month", "")
    import uuid
    invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
    invoice_data = {
        "client_id": client["id"],
        "invoice_number": invoice_number,
        "date": invoice_date,
        "month": month,
    }
    items = data.get("items", [])
    invoice = create_invoice(invoice_data, items)
    pending = get_pending_invoice(user_id)
    if pending:
        delete_pending_invoice(pending["id"])
    return {
        "status": "complete",
        "message": f"Invoice {invoice_number} created successfully!",
        "invoice": invoice,
    }