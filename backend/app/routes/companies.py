"""
Company routes — manage user's company profile.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_auth
from app.models import CompanyCreate
from app.invoice_service import create_company, get_company, update_company

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/me")
def get_my_company(claims: dict[str, Any] = Depends(require_auth)):
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        return {"company": None}
    return {"company": company}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_my_company(
    body: CompanyCreate,
    claims: dict[str, Any] = Depends(require_auth),
):
    user_id = claims.get("sub", "")
    existing = get_company(user_id)
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists.")
    company = create_company(user_id, body.model_dump())
    return {"company": company}


@router.put("/me")
def update_my_company(
    body: CompanyCreate,
    claims: dict[str, Any] = Depends(require_auth),
):
    user_id = claims.get("sub", "")
    existing = get_company(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found.")
    updated = update_company(existing["id"], body.model_dump(exclude_unset=True))
    return {"company": updated}
