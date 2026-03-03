"""
WhatsApp webhook routes — receives messages, processes with AI, creates invoices.
"""

from typing import Any

from fastapi import APIRouter, Depends

from app.auth import require_auth
from app.models import WhatsAppMessage
from app.ai_service import extract_invoice_data
from app.invoice_service import (
    get_company,
    get_client_by_name,
    create_invoice,
    create_pending_invoice,
    get_pending_invoice,
    delete_pending_invoice,
)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


@router.post("/webhook")
async def whatsapp_webhook(
    body: WhatsAppMessage,
    claims: dict[str, Any] = Depends(require_auth),
):
    """
    Process incoming WhatsApp messages:
    1. Extract invoice data with AI
    2. If incomplete, store in pending_invoices and return questions
    3. If complete, create the invoice and return confirmation
    """
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        return {
            "status": "error",
            "message": "Please set up your company profile first.",
        }

    # Process message with AI
    result = await extract_invoice_data(body.message)

    if result.get("status") == "error":
        return {
            "status": "error",
            "message": result.get("questions", ["An error occurred."])[0],
        }

    if result["status"] == "incomplete":
        # Store pending invoice
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

    # Look up client
    client = get_client_by_name(company["id"], data.get("client_name", ""))
    if not client:
        return {
            "status": "client_not_found",
            "message": f"Client '{data.get('client_name')}' not found. Would you like to create a new client?",
            "extracted_data": data,
        }

    # Create invoice
    from datetime import date as date_type

    invoice_date = data.get("date", str(date_type.today()))
    month = data.get("month", "")

    # Generate invoice number
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

    # Clean up any pending invoices
    pending = get_pending_invoice(user_id)
    if pending:
        delete_pending_invoice(pending["id"])

    return {
        "status": "complete",
        "message": f"Invoice {invoice_number} created successfully!",
        "invoice": invoice,
    }
