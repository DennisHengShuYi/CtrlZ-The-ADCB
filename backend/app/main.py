"""
FastAPI application — main entry point.
Routes:
  GET  /              → public health-check
  GET  /api/protected → requires valid Clerk JWT
  /api/companies/*    → company management
  /api/clients/*      → client management
  /api/invoices/*     → invoice management + PDF download
  /api/payments/*     → payment management
  /api/whatsapp/*     → WhatsApp webhook
"""

from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_auth
from app.config import PORT
from app.routers import instagram, product 

from app.routes.companies import router as companies_router
from app.routes.clients import router as clients_router
from app.routes.invoices import router as invoices_router
from app.routes.payments import router as payments_router
from app.routes.currency import router as currency_router
from app.routers.whatsapp import pillar1_router, invoice_router

app = FastAPI(
    title="CtrlZ-The-ADCB API",
    version="0.2.0",
    description="AI-Powered WhatsApp Invoice Generation System",
)

# CORS — allow the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──
app.include_router(companies_router)
app.include_router(clients_router)
app.include_router(invoices_router)
app.include_router(payments_router)
app.include_router(currency_router)


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
# Include Pillar 1 routers
# ──────────────────────────────────────
app.include_router(pillar1_router)
app.include_router(invoice_router)   # <-- add this line
app.include_router(instagram.router)
app.include_router(product.router)

# ──────────────────────────────────────
# Run with: python -m app.main
# ──────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
