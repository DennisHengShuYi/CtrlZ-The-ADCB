"""
Client routes — CRUD for a company's clients.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_auth
from app.models import ClientCreate
from app.invoice_service import (
    create_client,
    get_clients,
    get_client,
    update_client,
    delete_client,
    get_company,
)

router = APIRouter(prefix="/api/clients", tags=["clients"])


def _ensure_company(claims: dict) -> str:
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Create a company first.")
    return company["id"]


@router.get("/")
def list_clients(claims: dict[str, Any] = Depends(require_auth)):
    company_id = _ensure_company(claims)
    return {"clients": get_clients(company_id)}


@router.get("/{client_id}")
def get_single_client(client_id: str, claims: dict[str, Any] = Depends(require_auth)):
    _ensure_company(claims)
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    return {"client": client}


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_new_client(
    body: ClientCreate,
    claims: dict[str, Any] = Depends(require_auth),
):
    company_id = _ensure_company(claims)
    data = body.model_dump()
    data["company_id"] = company_id
    client = create_client(data)
    return {"client": client}


@router.put("/{client_id}")
def update_existing_client(
    client_id: str,
    body: ClientCreate,
    claims: dict[str, Any] = Depends(require_auth),
):
    _ensure_company(claims)
    updated = update_client(client_id, body.model_dump(exclude_unset=True))
    return {"client": updated}


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_client(client_id: str, claims: dict[str, Any] = Depends(require_auth)):
    _ensure_company(claims)
    delete_client(client_id)
