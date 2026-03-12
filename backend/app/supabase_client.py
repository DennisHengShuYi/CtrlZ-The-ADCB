"""
Supabase client — shared instance for all backend services.
Configured with extended timeouts, retry logic, and helpers for invoice pre-vet HITL storage.
"""

import os
import time
import functools
from typing import Any

from httpx import ConnectError, ConnectTimeout
from supabase import Client, ClientOptions, create_client

from app.config import ROOT_DIR, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL, USE_SUPABASE
from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

SUPABASE_URL: str = SUPABASE_URL or os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = SUPABASE_SERVICE_ROLE_KEY or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("⚠️  SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — DB calls will fail.")

# Extended timeouts: default is 5s which causes ConnectTimeout on slow networks
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    options=ClientOptions(
        postgrest_client_timeout=30,
        storage_client_timeout=30,
    ),
)


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator that retries a function on transient network errors
    (ConnectTimeout, ConnectError) with exponential backoff.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectTimeout, ConnectError) as e:
                    last_exc = e
                    delay = base_delay * (2**attempt)
                    print(
                        f"⚠️  Supabase connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
            raise last_exc

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            import asyncio

            last_exc = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (ConnectTimeout, ConnectError) as e:
                    last_exc = e
                    delay = base_delay * (2**attempt)
                    print(
                        f"⚠️  Supabase connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
            raise last_exc

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# Lazy-init wrapper that respects USE_SUPABASE flag (for environments without Supabase)
_client: Any = None


def get_supabase():
    """Return shared Supabase client if enabled, else None."""
    global _client
    if _client is not None:
        return _client
    if not USE_SUPABASE or not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    _client = supabase
    return _client


def save_prevet_result(invoice: dict, pre_vet: dict, source_file: str | None = None) -> str | None:
    """
    Save pre-vet result to Supabase. Saves all results.
    - HITL required: status = pending_review (needs approve)
    - No HITL: status = approved (shown but no approve needed)
    Returns record id if saved, else None.
    """
    sb = get_supabase()
    if not sb:
        return None

    # Only route cross-border (non-MYR) invoices to HITL for tariff calculation
    currency = invoice.get("currency", "MYR").upper()
    status = "pending_review" if currency != "MYR" else "approved"

    row = {
        "invoice_id": pre_vet.get("invoice_id", ""),
        "invoice_data": invoice,
        "pre_vet_result": pre_vet,
        "source_file": source_file or "",
        "status": status,
    }
    r = sb.table("invoice_prevet_results").insert(row).execute()
    if r.data and len(r.data) > 0:
        return r.data[0].get("id")
    return None


def get_hitl_queue(include_approved: bool = True) -> list[dict]:
    """
    Fetch invoices from Supabase.
    When include_approved=True, returns both pending_review and approved (uploaded items only).
    """
    sb = get_supabase()
    if not sb:
        return []

    r = sb.table("invoice_prevet_results").select("*").order(
        "created_at", desc=True
    ).execute()

    items = []
    for row in (r.data or []):
        status = row.get("status", "pending_review")
        if not include_approved and status == "approved":
            continue
        items.append(
            {
                "id": row["id"],
                "source_file": row.get("source_file", ""),
                "invoice": row.get("invoice_data", {}),
                "pre_vet": row.get("pre_vet_result", {}),
                "status": status,
                "created_at": row.get("created_at"),
            }
        )
    return items


def approve_prevet_result(record_id: str, reviewed_by: str) -> bool:
    """
    Mark a pre-vet result as approved.
    Syncs the approved tariff from pre_vet_result back to the 'invoices' table.
    Only updates pending_review records.
    """
    sb = get_supabase()
    if not sb:
        return False

    from datetime import datetime, timezone
    from decimal import Decimal

    # 1. Fetch the record to get tariff and invoice identifier
    res = sb.table("invoice_prevet_results").select("*").eq("id", record_id).execute()
    if not res.data:
        return False
    
    record = res.data[0]
    pre_vet = record.get("pre_vet_result", {})
    invoice_data = record.get("invoice_data", {})
    
    invoice_num = invoice_data.get("invoice_id") # This is 'invoice_id' in pillar2 schema, maps to 'invoice_number' in DB
    total_tariff = Decimal(str(pre_vet.get("total_tariff", 0.0)))

    # 2. Update the pre-vet result status
    now = datetime.now(timezone.utc).isoformat()
    r = (
        sb.table("invoice_prevet_results")
        .update(
            {
                "status": "approved",
                "reviewed_by": reviewed_by,
                "reviewed_at": now,
                "updated_at": now,
            }
        )
        .eq("id", record_id)
        .eq("status", "pending_review")
        .execute()
    )

    if not r.data:
        return False

    # 3. Sync to main invoices table
    # We match by invoice_number. 
    # Note: In a production system, we'd use a more robust link like invoice_id/PK.
    inv_res = sb.table("invoices").select("id, total_amount, tariff").eq("invoice_number", invoice_num).execute()
    if inv_res.data:
        inv = inv_res.data[0]
        inv_id = inv["id"]
        
        # Calculate new total = (old_total - old_tariff) + new_tariff
        old_total = Decimal(str(inv.get("total_amount", 0.0)))
        old_tariff = Decimal(str(inv.get("tariff", 0.0)))
        new_total = (old_total - old_tariff) + total_tariff
        
        sb.table("invoices").update({
            "tariff": str(total_tariff),
            "total_amount": str(new_total)
        }).eq("id", inv_id).execute()
        
        print(f"[HITL] Synced tariff {total_tariff} to invoice {invoice_num}. New total: {new_total}")

    return True
