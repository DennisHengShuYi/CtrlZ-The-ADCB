import os
import json
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, BackgroundTasks
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
from app.ai_service import extract_invoice_data, extract_receipt_data, classify_media_intent, extract_supplier_invoice_v2, evaluate_supplier_bill
from app.invoice_service import (
    get_company,
    get_client_by_name,
    create_invoice,
    create_pending_invoice,
    get_pending_invoice,
    delete_pending_invoice,
    create_client,
    match_receipt_to_invoice,
    create_payment,
    update_invoice_status,
    get_financial_summary
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


@invoice_router.post("/simulate-media")
async def simulate_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    sender_phone: str = Form(""),
    receiver_phone: str = Form(""),
    claims: dict[str, Any] = Depends(require_auth),
):
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Please set up your company profile first.")
    
    company_id = company["id"]
    
    image_bytes = await file.read()
    mime_type = file.content_type or "application/pdf"
    
    # 1. Extract OCR Data
    extracted = await extract_receipt_data(image_bytes, mime_type)
    if "error" in extracted:
        raise HTTPException(status_code=500, detail=extracted["error"])
        
    # 2. Match Client (Supplier)
    sender_name = extracted.get("sender_name") or extracted.get("bank_name") or "Unknown Supplier"
    client = get_client_by_name(company_id, sender_name)
    if not client:
        client = create_client({
            "company_id": company_id,
            "name": sender_name,
            "email": "",
            "phone": sender_phone,
            "address": "",
            "type": "supplier"
        })
        
    from datetime import datetime
    date_str = extracted.get("transaction_date") or str(datetime.today().date())
    try:
        month = date_str[:7]
    except:
        month = str(datetime.today().date())[:7]
        
    import uuid
    invoice_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
    invoice_data = {
        "client_id": client["id"],
        "invoice_number": invoice_number,
        "date": date_str,
        "month": month,
        "type": "receiving",
        "currency": extracted.get("currency", "MYR"),
    }
    
    amount = extracted.get("amount") or 0.0
    items = [{
        "description": "Supplier Bill (Scanned from Media)",
        "price": float(amount),
        "quantity": 1
    }]
    
    # 3. Create invoice with background auto-pay evaluation
    invoice = create_invoice(invoice_data, items, background_tasks=background_tasks)
    
    # 4. Terminal Output Logic
    terminal_data = {
      "event": "whatsapp_media_received",
      "metadata": {
        "sender": f"{sender_phone} ({sender_name})",
        "receiver": f"{receiver_phone}",
        "timestamp": datetime.utcnow().isoformat() + "Z"
      },
      "ocr_result": {
        "amount": float(amount),
        "currency": extracted.get("currency", "MYR"),
        "reference": extracted.get("reference_number", ""),
        "date": date_str
      },
      "automation_status": {
        "invoice_created": invoice_number,
        "auto_paid": "Pending background evaluation (check invoice status/badges)"
      }
    }
    
    print("\n" + "="*50)
    print("WHATSAPP SIMULATION REPORT:")
    print(json.dumps(terminal_data, indent=2))
    print("="*50 + "\n")
    
    return {
        "status": "success",
        "message": "Media simulated, bill created, and auto-pay evaluated.",
        "invoice": invoice,
        "simulation_report": terminal_data
    }


@invoice_router.post("/unified")
async def unified_whatsapp(
    background_tasks: BackgroundTasks,
    message: str = Form(""),
    file: Optional[UploadFile] = File(None),
    sender_phone: str = Form(""),
    receiver_phone: str = Form(""),
    claims: dict[str, Any] = Depends(require_auth),
):
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Please set up your company profile first.")
    
    company_id = company["id"]
    session_id = sender_phone or user_id

    # If Media Included
    if file and file.size > 0:
        image_bytes = await file.read()
        mime_type = file.content_type or "application/pdf"
        
        classification = await classify_media_intent(image_bytes, mime_type)
        detected_type = classification.get("detected_type")
        extracted_data = classification.get("extracted_data", {})
        
        reply_message = ""
        action_type = ""
        invoice_number = None

        if detected_type == "CUSTOMER_RECEIPT":
            matches = match_receipt_to_invoice(company_id, extracted_data)
            if matches and matches[0].get("match_score", 0) > 0:
                best_match = matches[0]
                invoice_id = best_match["id"]
                client_id = best_match["client_id"]
                
                # Check for amount otherwise fallback to invoice's total amount
                amount = extracted_data.get("amount")
                if not amount:
                     amount = best_match.get("total_amount", 0)
                
                from datetime import datetime
                date_str = extracted_data.get("transaction_date") or str(datetime.today().date())
                
                # Auto-pay
                create_payment({
                    "invoice_id": invoice_id,
                    "client_id": client_id,
                    "amount": float(amount),
                    "date": date_str,
                    "method": "AI Auto-Match",
                    "notes": f"🤖 Auto-matched from customer receipt. Ref: {extracted_data.get('reference_number', 'N/A')}",
                    "currency": extracted_data.get("currency", "MYR")
                })
                update_invoice_status(invoice_id, "paid")
                reply_message = f"Thanks! I've matched this to Invoice {best_match['invoice_number']}. Your balance is now $0."
                action_type = "receipt_matched"
                invoice_number = best_match['invoice_number']
            else:
                reply_message = "I received a receipt but couldn't confidently match it to any unpaid invoice. I've logged it for your review."
                action_type = "receipt_unmatched"
            
        elif detected_type == "SUPPLIER_INVOICE":
            # 1. Deep Extract
            deep_extracted = await extract_supplier_invoice_v2(image_bytes, mime_type)
            if "error" in deep_extracted:
                reply_message = "Failed to parse supplier invoice deeply."
                action_type = "error"
                store_message(session_id, "assistant", reply_message)
                return {"status": "error", "reply": reply_message, "action_type": action_type}
            
            sender_name = deep_extracted.get("vendor", {}).get("name") or "Unknown Supplier"
            client = get_client_by_name(company_id, sender_name)
            if not client:
                client = create_client({
                    "company_id": company_id,
                    "name": sender_name,
                    "email": deep_extracted.get("vendor", {}).get("contact", ""),
                    "phone": sender_phone,
                    "address": deep_extracted.get("vendor", {}).get("address", ""),
                    "type": "supplier"
                })
                
            from datetime import datetime
            date_str = deep_extracted.get("transaction_date") or str(datetime.today().date())
            try:
                month = date_str[:7]
            except:
                month = str(datetime.today().date())[:7]
                
            import uuid
            inv_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
            amount = deep_extracted.get("amount") or 0.0
            currency = deep_extracted.get("currency", "MYR")
            
            invoice_data = {
                "client_id": client["id"],
                "invoice_number": inv_number,
                "date": date_str,
                "month": month,
                "type": "receiving",
                "currency": currency,
            }
            items = []
            for lit in deep_extracted.get("line_items", []):
                items.append({
                    "description": lit.get("description", "Item"),
                    "price": float(lit.get("price", 0)),
                    "quantity": int(lit.get("quantity", 1))
                })
            
            if not items:
                items.append({
                    "description": "Supplier Bill (Scanned from Media)",
                    "price": float(amount),
                    "quantity": 1
                })
                
            # 2. Evaluate synchronously
            summary = get_financial_summary(company_id)
            cash_on_hand = summary["cash_on_hand"]
            available_for_expenses = summary["available_for_expenses"]
            base_currency = summary["base_currency"]
            
            ai_decision = await evaluate_supplier_bill(
                amount=amount,
                currency=currency,
                description="Supplier Invoice Extracted by AI",
                supplier_name=sender_name,
                cash_on_hand=cash_on_hand,
                available_for_expenses=available_for_expenses,
                base_currency=base_currency,
                line_items=deep_extracted.get("line_items", [])
            )
            
            decision = ai_decision.get("decision", "defer")
            
            # Create the invoice without background tasks since we do it here synchronously
            invoice = create_invoice(invoice_data, items)
            invoice_number = inv_number
            
            if decision == "approve":
                create_payment({
                    "invoice_id": invoice["id"],
                    "client_id": client["id"],
                    "amount": float(amount),
                    "date": date_str,
                    "method": "AI Auto-Pay",
                    "notes": f"🤖 Auto-paid by AI: {ai_decision.get('reason', 'OK')}",
                    "currency": currency
                })
                update_invoice_status(invoice["id"], "paid")
                reply_message = f"Invoice received and verified. Your payment of ${amount} has been processed via AI Auto-Pay."
                action_type = "supplier_invoice_approved"
            elif decision == "negotiate":
                update_invoice_status(invoice["id"], "pending_negotiation")
                reply_message = ai_decision.get("negotiation_message") or f"Budget Limit Reached. Sending counter-offer to Supplier..."
                action_type = "supplier_invoice_negotiate"
            else:
                update_invoice_status(invoice["id"], "unpaid")
                reply_message = "Not enough cash to process this invoice. Deferred."
                action_type = "supplier_invoice_deferred"
            
        else:
            reply_message = "That's a nice photo! Did you want to send a receipt or ask about a product?"
            action_type = "irrelevant_media"
            
        # Store AI response
        user_msg = message + " [Attached Media]" if message else "[Attached Media]"
        store_message(session_id, "user", user_msg, intent="media_upload", mood="neutral")
        store_message(session_id, "assistant", reply_message)
        
        return {
            "status": "success",
            "reply": reply_message,
            "detected_type": detected_type,
            "extracted_data": extracted_data,
            "action_type": action_type,
            "invoice_number": invoice_number
        }
        
    else: # Text Only
        history = get_conversation_history(session_id, limit=5)
        text_content = message
        
        try:
            if client:
                result = classify_with_gemini(text_content, history)
            else:
                result = fallback_classify(text_content)
        except Exception as e:
            print(f"Unified fallback error: {e}")
            result = fallback_classify(text_content)
            
        store_message(session_id, "user", text_content, intent=result.get("intent"), mood=result.get("mood"))
        store_message(session_id, "assistant", result.get("reply"))
        
        return {
            "status": "success",
            "reply": result.get("reply"),
            "intent": result.get("intent"),
            "mood": result.get("mood"),
            "action_type": "text_chat"
        }