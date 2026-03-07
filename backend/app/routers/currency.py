"""
Currency routes — fetch live exchange rates via CurrencyLayer.
Accepts query params: ?from=USD&to=MYR  (aliased as from_currency / base_currency)
"""

from fastapi import APIRouter, Query
from app.currency_service import fetch_exchange_rate

router = APIRouter(prefix="/api/currency", tags=["currency"])


@router.get("/rate")
async def get_rate(
    from_currency: str = Query(None, alias="from"),
    base_currency: str = Query(None, alias="to"),
    # Also accept the old parameter names for backwards-compat
    from_curr: str = Query(None, alias="from_currency"),
    base_curr: str = Query(None, alias="base_currency"),
):
    """
    Get the live exchange rate between two currencies.
    Accepts: ?from=USD&to=MYR  OR  ?from_currency=USD&base_currency=MYR
    """
    src = from_currency or from_curr or "USD"
    dst = base_currency or base_curr or "MYR"
    rate = await fetch_exchange_rate(src, dst)
    return {"from": src.upper(), "to": dst.upper(), "rate": float(rate)}
