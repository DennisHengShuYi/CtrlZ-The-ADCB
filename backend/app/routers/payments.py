"""
Payment routes — CRUD for payments.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from app.auth import require_auth
from app.models import PaymentCreate, PaymentVerificationRequest
from app.pdf_service import generate_receipt_pdf
from app.ai_service import extract_receipt_data
import io
from fastapi.responses import StreamingResponse
from app.invoice_service import (
    create_payment,
    get_payments,
    get_payment,
    delete_payment,
    get_company,
    get_invoice,
    match_receipt_to_invoice,
    process_payment_verification,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _ensure_company(claims: dict) -> str:
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Create a company first.")
    return company["id"], company


@router.get("/")
def list_payments(claims: dict[str, Any] = Depends(require_auth)):
    company_id, _ = _ensure_company(claims)
    return {"payments": get_payments(company_id)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_new_payment(
    body: PaymentCreate,
    claims: dict[str, Any] = Depends(require_auth),
):
    company_id, _ = _ensure_company(claims)
    payment = create_payment(body.model_dump())
    return {"payment": payment}


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_payment(payment_id: str, claims: dict[str, Any] = Depends(require_auth)):
    _ensure_company(claims)
    delete_payment(payment_id)


@router.post("/scan-receipt")
async def scan_receipt(
    file: UploadFile = File(...), claims: dict[str, Any] = Depends(require_auth)
):
    company_id, _ = _ensure_company(claims)
    image_bytes = await file.read()
    mime_type = file.content_type or "image/jpeg"

    # 1. AI OCR to grab data
    extracted = await extract_receipt_data(image_bytes, mime_type)
    if "error" in extracted:
        raise HTTPException(status_code=500, detail=extracted["error"])

    # 2. Match with database invoices
    matches = match_receipt_to_invoice(company_id, extracted)

    return {"extracted_data": extracted, "suggested_matches": matches}


@router.post("/verify")
def verify_payment(
    body: PaymentVerificationRequest, claims: dict[str, Any] = Depends(require_auth)
):
    company_id, _ = _ensure_company(claims)
    payment = process_payment_verification(company_id, body.model_dump())
    return {
        "message": "Payment verified and invoice updated successfully!",
        "payment": payment,
    }


@router.get("/{payment_id}/pdf")
def download_receipt_pdf(
    payment_id: str, invoice_id: str, claims: dict[str, Any] = Depends(require_auth)
):
    _, company = _ensure_company(claims)
    payment = get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_bytes = generate_receipt_pdf(payment, invoice, company)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="receipt_{payment_id[:8]}.pdf"'
        },
    )
