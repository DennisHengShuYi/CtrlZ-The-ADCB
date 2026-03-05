"""
Invoice routes — CRUD + PDF download for invoices.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
import io

from app.auth import require_auth
from app.models import InvoiceCreate, InvoiceStatusUpdate
from app.invoice_service import (
    create_invoice,
    get_invoices,
    get_invoice,
    update_invoice_status,
    delete_invoice,
    get_company,
    get_net_balance,
)
from app.pdf_service import generate_invoice_pdf

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _ensure_company(claims: dict) -> tuple[str, dict]:
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Create a company first.")
    return company["id"], company


@router.get("/")
def list_invoices(claims: dict[str, Any] = Depends(require_auth)):
    company_id, _ = _ensure_company(claims)
    return {"invoices": get_invoices(company_id)}


@router.get("/{invoice_id}")
def get_single_invoice(invoice_id: str, claims: dict[str, Any] = Depends(require_auth)):
    _ensure_company(claims)
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return {"invoice": invoice}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_new_invoice(
    body: InvoiceCreate,
    background_tasks: BackgroundTasks,
    claims: dict[str, Any] = Depends(require_auth),
):
    _ensure_company(claims)
    items = [item.model_dump() for item in body.items]
    invoice = create_invoice(
        body.model_dump(exclude={"items"}), items, background_tasks=background_tasks
    )
    return {"invoice": invoice}


@router.patch("/{invoice_id}/status")
def patch_invoice_status(
    invoice_id: str,
    body: InvoiceStatusUpdate,
    claims: dict[str, Any] = Depends(require_auth),
):
    _ensure_company(claims)
    updated = update_invoice_status(invoice_id, body.status)
    return {"invoice": updated}


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_invoice(invoice_id: str, claims: dict[str, Any] = Depends(require_auth)):
    _ensure_company(claims)
    delete_invoice(invoice_id)


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    claims: dict[str, Any] = Depends(require_auth),
):
    _, company = _ensure_company(claims)
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    pdf_bytes = generate_invoice_pdf(invoice, company)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="invoice_{invoice["invoice_number"]}.pdf"'
        },
    )


@router.get("/balance/{client_id}/{month}")
def get_client_balance(
    client_id: str,
    month: str,
    claims: dict[str, Any] = Depends(require_auth),
):
    _ensure_company(claims)
    balance = get_net_balance(client_id, month)
    return {"balance": balance}
