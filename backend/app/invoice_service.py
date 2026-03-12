"""
Invoice Service — CRUD operations for invoices, clients, companies, payments.
Uses the Supabase client for all DB operations.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional

from app.supabase_client import supabase, with_retry
from fastapi import BackgroundTasks, HTTPException


# ═══════════════════════════════════════════
# Companies
# ═══════════════════════════════════════════
def create_company(user_id: str, data: dict) -> dict:
    payload = {**data, "user_id": user_id}
    result = supabase.table("user_companies").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


@with_retry()
def get_company(user_id: str) -> Optional[dict]:
    result = (
        supabase.table("user_companies")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


@with_retry()
async def get_company_with_fallback(user_id: str) -> Optional[dict]:
    """Get company for user, falling back to first available record in mock/dev mode."""
    company = get_company(user_id)
    if company:
        return company
    # Fallback for mock mode users
    result = supabase.table("user_companies").select("*").order("created_at").limit(1).execute()
    return result.data[0] if result.data else None


def update_company(company_id: str, data: dict) -> dict:
    result = (
        supabase.table("user_companies").update(data).eq("id", company_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


# ═══════════════════════════════════════════
# Clients
# ═══════════════════════════════════════════
@with_retry()
def create_client(data: dict) -> dict:
    result = supabase.table("clients").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


@with_retry()
def get_clients(company_id: str) -> list[dict]:
    result = (
        supabase.table("clients")
        .select("*")
        .eq("company_id", company_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@with_retry()
def get_client_by_name(company_id: str, name: str) -> Optional[dict]:
    result = (
        supabase.table("clients")
        .select("*")
        .eq("company_id", company_id)
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


@with_retry()
def get_client_by_phone(company_id: str, phone_number: str) -> Optional[dict]:
    result = (
        supabase.table("clients")
        .select("*")
        .eq("company_id", company_id)
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


@with_retry()
def get_client(client_id: str) -> Optional[dict]:
    result = (
        supabase.table("clients").select("*").eq("id", client_id).limit(1).execute()
    )
    return result.data[0] if result.data else None


def update_client(client_id: str, data: dict) -> dict:
    result = supabase.table("clients").update(data).eq("id", client_id).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


def delete_client(client_id: str) -> bool:
    # Delete child invoice_items via invoices first
    inv_res = supabase.table("invoices").select("id").eq("client_id", client_id).execute()
    invoice_ids = [inv["id"] for inv in (inv_res.data or [])]
    if invoice_ids:
        for inv_id in invoice_ids:
            supabase.table("invoice_items").delete().eq("invoice_id", inv_id).execute()
        supabase.table("invoices").delete().in_("id", invoice_ids).execute()
    # Delete payments
    supabase.table("payments").delete().eq("client_id", client_id).execute()
    # Delete client
    supabase.table("clients").delete().eq("id", client_id).execute()
    return True


# ═══════════════════════════════════════════
# Invoices
# ═══════════════════════════════════════════
def _safe_date(raw) -> str:
    """Ensure a value is a valid YYYY-MM-DD date string for Supabase."""
    from datetime import date, datetime
    today = date.today()
    if not raw:
        return str(today)
    s = str(raw).strip()
    # Already valid ISO date
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        pass
    # Day-only: "09"
    if s.isdigit() and len(s) <= 2:
        day = int(s)
        if 1 <= day <= 31:
            try:
                return str(today.replace(day=day))
            except ValueError:
                pass
    return str(today)


def create_invoice(invoice_data: dict, items: list[dict], background_tasks: BackgroundTasks = None, save_items: bool = True) -> dict:
    # Calculate total
    total = sum(Decimal(str(item["price"])) * item["quantity"] for item in items)

    # Defensive: ensure date is valid YYYY-MM-DD before sending to Supabase
    safe_date = _safe_date(invoice_data.get("date"))
    safe_month = invoice_data.get("month", safe_date[:7])
    if len(safe_month) < 7 or safe_month[4:5] != '-':
        safe_month = safe_date[:7]

    invoice_type = invoice_data.get("type", "issuing")

    tariff = Decimal(str(invoice_data.get("tariff", 0.0)))
    total_amount = total + tariff

    payload = {
        "client_id": invoice_data["client_id"],
        "invoice_number": invoice_data["invoice_number"],
        "date": safe_date,
        "month": safe_month,
        "currency": invoice_data.get("currency", "MYR"),
        "type": invoice_type,
        "exchange_rate": str(Decimal(str(invoice_data.get("exchange_rate", 1.0)))),
        "tariff": str(tariff),
        "total_amount": str(total_amount),
        "notes": invoice_data.get("notes"),
    }

    result = supabase.table("invoices").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create invoice.")
    invoice = result.data[0]

    # Resolve company_id for product matching
    client = get_client(invoice["client_id"])
    company_id = client["company_id"] if client else None

    if save_items:
        # Insert items + link to products + sync inventory
        for item in items:
            item_desc = item.get("description", "")
            item_qty = item.get("quantity", 0)

            # Match item to a product in the database
            matched_product = None
            if company_id:
                matched_product = get_product_by_name(company_id, item_desc)

            item_payload = {
                "invoice_id": invoice["id"],
                "description": item_desc,
                "price": str(Decimal(str(item["price"]))),
                "quantity": item_qty,
            }
            if item.get("unit"):
                item_payload["unit"] = item["unit"]
            if item.get("origin_country"):
                item_payload["origin_country"] = item["origin_country"]
            if item.get("unit_price") is not None:
                item_payload["unit_price"] = str(Decimal(str(item["unit_price"])))

            # Link product_id if matched
            if matched_product:
                item_payload["product_id"] = matched_product["id"]

            insert_result = supabase.table("invoice_items").insert(item_payload).execute()
            if not insert_result.data:
                print(f"WARNING: Failed to insert invoice item: {item_payload}")

            if not matched_product and company_id:
                print(
                    f"[Inventory] WARNING: No product match for '{item_desc}'. Consider mapping it."
                )

    # ── HITL Routing ──
    # Ensure cross-border invoices (non-MYR) are queued for HITL/Tariff calc
    if invoice.get("currency", "MYR").upper() != "MYR" and background_tasks:
        # Pass items directly if they weren't saved to DB
        items_payload = items if not save_items else None
        background_tasks.add_task(_trigger_hitl_prevet, invoice["id"], items_payload)

    return get_invoice(invoice["id"])


def _trigger_hitl_prevet(invoice_id: str, items_override: list[dict] = None):
    """
    Background task to run AHTN classification on an invoice and push it to HITL queue.
    """
    from app.pillar2.invoice_prevet import pre_vet_invoice
    from app.supabase_client import save_prevet_result
    
    # 1. Fetch full invoice details
    res = supabase.table("invoices").select("*").eq("id", invoice_id).execute()
    if not res.data:
        print(f"[HITL] Error: Invoice {invoice_id} not found.")
        return
    invoice = res.data[0]
    invoice_num = invoice.get("invoice_number", "")

    # 1b. DO NOT trigger if already in HITL queue
    existing = supabase.table("invoice_prevet_results").select("id").eq("invoice_id", invoice_num).execute()
    if existing.data:
        return

    # 2. Get line items (either from arg or DB)
    if items_override:
        db_items = items_override
    else:
        items_res = supabase.table("invoice_items").select("*").eq("invoice_id", invoice_id).execute()
        db_items = items_res.data or []
    
    if not db_items:
        print(f"[HITL] Error: No line items found for invoice {invoice_id}.")
        return

    # 2. Get Client and Company details
    client = get_client(invoice["client_id"])
    company_id = client["company_id"] if client else None
    
    company = None
    if company_id:
        c_res = supabase.table("user_companies").select("*").eq("id", company_id).execute()
        if c_res.data:
            company = c_res.data[0]
    
    # 3. Construct the 'Invoice' schema for pre_vet_invoice
    invoice_type = invoice.get("type", "issuing")
    
    comp_data = {
        "name": company.get("name", "Unknown Company") if company else "Unknown Company",
        "address": company.get("address", "Unknown Address") if company else "Unknown Address",
        "country": "MY" 
    }
    client_data = {
        "name": client.get("name", "Unknown Client") if client else "Unknown Client",
        "address": client.get("address", "Unknown Address") if client else "Unknown Address",
        "country": client.get("country", "SG") if client else "SG"
    }

    line_items = []
    for it in db_items:
        line_items.append({
            "item_id": it.get("id", "temp_id"),
            "description": it["description"],
            "quantity": it["quantity"],
            "unit": it.get("unit", "pcs"),
            "unit_price": float(it.get("unit_price", it.get("price", 0))),
            "amount": float(it.get("amount", float(it.get("price", 0)) * it["quantity"]))
        })

    inv_dict = {
        "invoice_id": invoice_num,
        "date": str(invoice["date"]),
        "type": invoice_type,
        "seller": comp_data if invoice_type == "issuing" else client_data,
        "buyer": client_data if invoice_type == "issuing" else comp_data,
        "line_items": line_items,
        "total_amount": float(invoice["total_amount"]),
        "subtotal": sum(li["amount"] for li in line_items),
        "currency": invoice.get("currency", "MYR"),
        "notes": invoice.get("notes", "")
    }
    
    # 4. Run Pre-vet
    try:
        result = pre_vet_invoice(inv_dict)
        # 5. Save to HITL queue
        source_label = "WhatsApp Order" if "WhatsApp" in inv_dict.get("notes", "") else "Manual Entry"
        save_prevet_result(inv_dict, result, source_file=source_label)
    except Exception as e:
        print(f"[HITL] Failed to trigger pre-vet for invoice {invoice_id}: {e}")


# ═══════════════════════════════════════════
# Inventory Helpers (for Agentic Restock)
# ═══════════════════════════════════════════
@with_retry()
def get_product_by_name(company_id: str, name: str) -> Optional[dict]:
    """Fuzzy match a product by name within a company."""
    result = (
        supabase.table("products")
        .select("*")
        .eq("company_id", company_id)
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


@with_retry()
def update_product_inventory(product_id: str, new_inventory: int) -> dict:
    """Set absolute inventory for a product."""
    from datetime import datetime
    result = (
        supabase.table("products")
        .update({"inventory": new_inventory, "updated_at": datetime.utcnow().isoformat()})
        .eq("id", product_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to update product inventory.")
    return result.data[0]


@with_retry()
def adjust_product_inventory(product_id: str, delta: int) -> Optional[int]:
    """
    Atomically adjust inventory by delta (+/-).
    Tries the RPC stored procedure first (race-condition safe),
    falls back to read-modify-write if the RPC doesn't exist yet.
    Returns the new inventory value, or None on failure.
    """
    # Try atomic RPC first
    try:
        rpc_result = supabase.rpc("adjust_inventory", {
            "p_product_id": product_id,
            "p_delta": delta,
        }).execute()
        if rpc_result.data is not None:
            new_val = rpc_result.data
            print(f"[Inventory] Atomic RPC: product {product_id[:8]}... delta={delta:+d} -> new stock={new_val}")
            return new_val
    except Exception:
        pass  # RPC not available, fall back

    # Fallback: read-modify-write
    from datetime import datetime
    product = supabase.table("products").select("inventory").eq("id", product_id).limit(1).execute()
    if not product.data:
        return None
    current = product.data[0].get("inventory", 0)
    new_val = max(0, current + delta)
    supabase.table("products").update({
        "inventory": new_val,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", product_id).execute()
    print(f"[Inventory] Fallback: product {product_id[:8]}... {current} {delta:+d} -> {new_val}")
    return new_val


def get_invoices(company_id: str, background_tasks=None) -> list[dict]:
    # 1. Fetch clients for this company
    clients = supabase.table("clients").select("id, name").eq("company_id", company_id).execute().data
    client_ids = [c["id"] for c in clients]
    client_map = {c["id"]: c["name"] for c in clients}

    if not client_ids:
        return []

    # 2. Fetch invoices for these clients
    invoices = supabase.table("invoices").select("*").in_("client_id", client_ids).order("date", desc=True).execute().data or []

    # 3. Fetch HITL statuses from invoice_prevet_results
    invoice_nums = [inv["invoice_number"] for inv in invoices]
    hitl_res = supabase.table("invoice_prevet_results").select("invoice_id, status").in_("invoice_id", invoice_nums).execute().data or []
    hitl_map = {r["invoice_id"]: r["status"] for r in hitl_res}

    # 4. Map client names and HITL status
    for inv in invoices:
        inv["client_name"] = client_map.get(inv["client_id"], "Unknown")
        inv["hitl_status"] = hitl_map.get(inv["invoice_number"], "approved") 

    return invoices


@with_retry()
def get_invoice(invoice_id: str) -> Optional[dict]:
    result = (
        supabase.table("invoices").select("*").eq("id", invoice_id).limit(1).execute()
    )
    if not result.data:
        return None

    invoice = result.data[0]

    # Get items
    items_result = (
        supabase.table("invoice_items")
        .select("*")
        .eq("invoice_id", invoice_id)
        .execute()
    )
    invoice["items"] = items_result.data

    # Get client name
    client = get_client(invoice["client_id"])
    invoice["client_name"] = client["name"] if client else "Unknown"

    return invoice


def update_invoice_status(invoice_id: str, status: str) -> dict:
    current = supabase.table("invoices").select("status, type").eq("id", invoice_id).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    
    current_status = current.data[0].get("status", "unpaid")
    invoice_type = current.data[0].get("type", "issuing")

    result = (
        supabase.table("invoices")
        .update({"status": status})
        .eq("id", invoice_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
        
    # Deduct inventory ONLY when invoice shifts to "paid" status
    if status == "paid" and current_status != "paid":
        items = supabase.table("invoice_items").select("*").eq("invoice_id", invoice_id).execute().data or []
        for item in items:
            product_id = item.get("product_id")
            if not product_id:
                continue
            qty = int(item.get("quantity", 0))
            if qty > 0:
                delta = -qty if invoice_type == "issuing" else qty
                if delta != 0:
                    new_val = adjust_product_inventory(product_id, delta)
                    print(f"[Inventory] Paid -> Updated product {product_id[:8]} by {delta}. New stock: {new_val}")

    return result.data[0]


def delete_invoice(invoice_id: str) -> bool:
    # Delete child items first to avoid FK constraint errors
    supabase.table("invoice_items").delete().eq("invoice_id", invoice_id).execute()
    supabase.table("invoices").delete().eq("id", invoice_id).execute()
    return True


# ═══════════════════════════════════════════
# Payments
# ═══════════════════════════════════════════
@with_retry()
def create_payment(data: dict) -> dict:
    payload = {
        "client_id": data["client_id"],
        "amount": str(Decimal(str(data["amount"]))),
        "date": str(data["date"]),
        "method": data.get("method"),
        "notes": data.get("notes"),
        "currency": data.get("currency", "MYR"),
        "exchange_rate": str(Decimal(str(data.get("exchange_rate", 1.0)))),
    }
    result = supabase.table("payments").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


def get_payments(company_id: str) -> list[dict]:
    clients = get_clients(company_id)
    if not clients:
        return []

    client_ids = [c["id"] for c in clients]
    client_map = {c["id"]: c["name"] for c in clients}

    result = (
        supabase.table("payments")
        .select("*")
        .in_("client_id", client_ids)
        .order("date", desc=True)
        .execute()
    )

    payments = result.data
    for p in payments:
        p["client_name"] = client_map.get(p["client_id"], "Unknown")

    return payments


def get_payment(payment_id: str) -> dict | None:
    result = supabase.table("payments").select("*").eq("id", payment_id).execute()
    return result.data[0] if result.data else None


def delete_payment(payment_id: str) -> bool:
    supabase.table("payments").delete().eq("id", payment_id).execute()
    return True


# ═══════════════════════════════════════════
# Net Balance
# ═══════════════════════════════════════════
def get_net_balance(client_id: str, month: str) -> dict:
    """
    Calculate net balance for a client for a given month.
    month format: "YYYY-MM" (e.g., "2024-03")
    """
    # Total invoiced
    inv_result = (
        supabase.table("invoices")
        .select("total_amount")
        .eq("client_id", client_id)
        .eq("month", month)
        .execute()
    )
    total_invoiced = sum(
        Decimal(str(inv.get("total_amount", 0))) for inv in inv_result.data
    )

    # Total paid
    pay_result = (
        supabase.table("payments")
        .select("amount, date")
        .eq("client_id", client_id)
        .execute()
    )
    # Filter payments by month
    total_paid = Decimal(0)
    for p in pay_result.data:
        if p["date"] and p["date"][:7] == month:
            total_paid += Decimal(str(p["amount"]))

    client = get_client(client_id)

    return {
        "client_id": client_id,
        "client_name": client["name"] if client else "Unknown",
        "month": month,
        "total_invoiced": str(total_invoiced),
        "total_paid": str(total_paid),
        "net_balance": str(total_invoiced - total_paid),
    }


# ═══════════════════════════════════════════
# Pending Invoices (AI conversational state)
# ═══════════════════════════════════════════
def create_pending_invoice(
    user_id: str, raw_message: str, extracted_data: dict, missing_fields: list[str]
) -> dict:
    payload = {
        "user_id": user_id,
        "raw_message": raw_message,
        "extracted_data": extracted_data,
        "missing_fields": missing_fields,
    }
    result = supabase.table("pending_invoices").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


def get_pending_invoice(user_id: str) -> Optional[dict]:
    result = (
        supabase.table("pending_invoices")
        .select("*")
        .eq("user_id", user_id)
        .order("last_interaction", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_pending_invoice(pending_id: str) -> bool:
    supabase.table("pending_invoices").delete().eq("id", pending_id).execute()
    return True


# ═══════════════════════════════════════════
# Receipt Matching & Financial Summary
# ═══════════════════════════════════════════
def match_receipt_to_invoice(company_id: str, extracted_data: dict) -> list[dict]:
    amount = extracted_data.get("amount")
    ref = extracted_data.get("reference_number")
    receipt_currency = extracted_data.get("currency", "MYR")

    query = (
        supabase.table("invoices")
        .select("*, clients!inner(company_id, name)")
        .eq("clients.company_id", company_id)
        .in_("status", ["unpaid", "partially_paid"])
    )
    result = query.execute()
    invoices = result.data

    matches = []
    for inv in invoices:
        match_score = 0

        # Direct amount match
        if amount and Decimal(str(inv["total_amount"])) == Decimal(str(amount)):
            match_score += 1

        # Cross-currency match: convert receipt amount to base, compare with invoice base
        if amount and match_score == 0:
            inv_base = Decimal(str(inv["total_amount"])) * Decimal(str(inv.get("exchange_rate", 1.0)))
            # If receipt currency differs, try matching base-equivalent amounts (within 2% tolerance)
            if receipt_currency and receipt_currency != inv.get("currency"):
                try:
                    tolerance = inv_base * Decimal("0.02")
                    receipt_dec = Decimal(str(amount))
                    if abs(receipt_dec - inv_base) <= tolerance:
                        match_score += 1
                except Exception:
                    pass

        # Reference number match
        if ref and str(ref).lower() in inv["invoice_number"].lower():
            match_score += 2

        if match_score > 0:
            inv["match_score"] = match_score
            inv["client_name"] = inv.get("clients", {}).get("name", "Unknown")
            matches.append(inv)

    matches.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return matches


def process_payment_verification(company_id: str, payment_data: dict) -> dict:
    payment = create_payment(payment_data)
    update_invoice_status(payment_data["invoice_id"], "paid")
    return payment


@with_retry()
def get_financial_summary(company_id: str) -> dict:
    clients = get_clients(company_id)
    company_res = supabase.table("user_companies").select("base_currency").eq("id", company_id).execute()
    base_currency = company_res.data[0].get("base_currency", "MYR") if company_res.data else "MYR"

    if not clients:
        return {
            "cash_on_hand": "0",
            "total_assets": "0",
            "available_for_expenses": "0",
            "base_currency": base_currency,
            "client_pending": [],
            "supplier_pending": [],
        }

    # Fetch all payments related to this company through clients
    payments_res = (
        supabase.table("payments")
        .select("*, clients!inner(type, company_id, name)")
        .eq("clients.company_id", company_id)
        .execute()
    )
    payments = payments_res.data or []

    cash_in = sum(
        (Decimal(str(p["amount"])) * Decimal(str(p.get("exchange_rate", 1.0))))
        for p in payments if p["clients"]["type"] in ("customer", None)
    )
    cash_out = sum(
        (Decimal(str(p["amount"])) * Decimal(str(p.get("exchange_rate", 1.0))))
        for p in payments if p["clients"]["type"] == "supplier"
    )
    cash_on_hand = cash_in - cash_out

    # Fetch all invoices related to this company through clients
    invoices_res = (
        supabase.table("invoices")
        .select("*, clients!inner(type, company_id, name)")
        .eq("clients.company_id", company_id)
        .in_("status", ["unpaid", "partially_paid"])
        .execute()
    )
    invoices = invoices_res.data or []

    client_pending = [
        inv for inv in invoices if inv.get("type", "issuing") == "issuing"
    ]
    supplier_pending = [
        inv for inv in invoices if inv.get("type", "issuing") == "receiving"
    ]

    accounts_receivable = sum(Decimal(str(inv.get("total_amount", 0))) * Decimal(str(inv.get("exchange_rate", 1.0))) for inv in client_pending)
    accounts_payable = sum(Decimal(str(inv.get("total_amount", 0))) * Decimal(str(inv.get("exchange_rate", 1.0))) for inv in supplier_pending)

    total_assets = cash_on_hand + accounts_receivable
    available_for_expenses = cash_on_hand - accounts_payable

    return {
        "cash_on_hand": str(cash_on_hand),
        "total_assets": str(total_assets),
        "available_for_expenses": str(available_for_expenses),
        "base_currency": base_currency,
        "client_pending": client_pending,
        "supplier_pending": supplier_pending,
    }


async def evaluate_auto_payment(invoice_id: str, client_id: str, company_id: str) -> None:
    from app.ai_service import evaluate_supplier_bill
    from datetime import date

    # Get the invoice data
    invoice = get_invoice(invoice_id)
    if not invoice or invoice.get("type") != "receiving":
        return

    # Get financial summary
    summary = get_financial_summary(company_id)
    cash_on_hand = Decimal(str(summary["cash_on_hand"]))
    available_for_expenses = Decimal(str(summary["available_for_expenses"]))
    base_currency = summary["base_currency"]

    inv_amount = Decimal(str(invoice["total_amount"]))
    inv_currency = invoice["currency"]
    inv_desc = "Auto-evaluating newly received invoice"
    supplier_name = invoice.get("client_name", "Supplier")
    exchange_rate = Decimal(str(invoice.get("exchange_rate", 1.0)))
    inv_amount_base = inv_amount * exchange_rate

    if inv_amount_base > cash_on_hand:
        print(f"Auto-payment aborted: insufficient cash for invoice {invoice_id}")
        return
        
    ai_decision = await evaluate_supplier_bill(
        amount=float(inv_amount),
        currency=inv_currency,
        description=inv_desc,
        supplier_name=supplier_name,
        cash_on_hand=float(cash_on_hand),
        available_for_expenses=float(available_for_expenses),
        base_currency=base_currency,
    )

    if ai_decision.get("decision") == "approve":
        reason = ai_decision.get("reason", "Approved by AI based on cash flow.")
        payment_payload = {
            "invoice_id": invoice_id,
            "client_id": client_id,
            "amount": str(inv_amount),
            "date": str(date.today()),
            "method": "AI Auto-Pay",
            "notes": f"Auto-paid by AI: {reason}",
            "currency": inv_currency,
            "exchange_rate": str(exchange_rate),
        }
        create_payment(payment_payload)
        update_invoice_status(invoice_id, "paid")
        supabase.table("invoices").update({"ai_auto_paid_reason": reason}).eq("id", invoice_id).execute()
        print(f"Auto-payment triggered successfully for invoice {invoice_id}")
    else:
        print(f"Auto-payment rejected by AI for invoice {invoice_id}")
