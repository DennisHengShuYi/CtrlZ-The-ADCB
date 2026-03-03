"""
Payment routes — CRUD for payments.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_auth
from app.models import PaymentCreate
from app.invoice_service import (
    create_payment,
    get_payments,
    delete_payment,
    get_company,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _ensure_company(claims: dict) -> str:
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Create a company first.")
    return company["id"]


@router.get("/")
def list_payments(claims: dict[str, Any] = Depends(require_auth)):
    company_id = _ensure_company(claims)
    return {"payments": get_payments(company_id)}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_new_payment(
    body: PaymentCreate,
    claims: dict[str, Any] = Depends(require_auth),
):
    _ensure_company(claims)
    payment = create_payment(body.model_dump())
    return {"payment": payment}


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_payment(payment_id: str, claims: dict[str, Any] = Depends(require_auth)):
    _ensure_company(claims)
    delete_payment(payment_id)
