"""
FastAPI application — main entry point.
Mirrors the same routes as the previous Express backend:
  GET /                    → public health-check
  GET /api/protected       → requires valid Clerk JWT
  POST /api/invoice/pre-vet → pre-vet invoice (RAG + LLM + tariff + flags)
"""

from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_auth
from app.config import PORT
from app.pillar2.invoice_prevet import pre_vet_invoice
from app.pillar2.schemas import Invoice

app = FastAPI(
    title="CtrlZ-The-ADCB API",
    version="0.1.0",
)

# CORS — allow the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────
# Public route
# ──────────────────────────────────────
@app.get("/")
def health_check():
    return {"message": "Backend server is running!"}


# ──────────────────────────────────────
# Protected route — requires Clerk JWT
# ──────────────────────────────────────
@app.get("/api/protected")
def protected_route(claims: dict[str, Any] = Depends(require_auth)):
    user_id = claims.get("sub", "unknown")
    return {"message": f"Authenticated! Your userId is: {user_id}"}


# ──────────────────────────────────────
# Invoice pre-vet (Schema Enforcement + AHTN RAG + LLM + HITL routing)
# ──────────────────────────────────────
@app.post("/api/invoice/pre-vet")
def invoice_pre_vet(invoice: Invoice):
    """
    Pre-vet an invoice: classify line items against AHTN, calculate tariffs,
    flag inconsistencies. Items with confidence < 90% are flagged for HITL.
    """
    try:
        result = pre_vet_invoice(invoice.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ──────────────────────────────────────
# Run with: python -m app.main
# ──────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
