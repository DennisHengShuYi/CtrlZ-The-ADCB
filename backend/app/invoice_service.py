"""
Invoice Service — CRUD operations for invoices, clients, companies, payments.
Uses the Supabase client for all DB operations.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional

from app.supabase_client import supabase
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


def get_company(user_id: str) -> Optional[dict]:
    result = (
        supabase.table("user_companies")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
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
def create_client(data: dict) -> dict:
    result = supabase.table("clients").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


def get_clients(company_id: str) -> list[dict]:
    result = (
        supabase.table("clients")
        .select("*")
        .eq("company_id", company_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


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
def create_invoice(invoice_data: dict, items: list[dict], background_tasks: BackgroundTasks = None) -> dict:
    # Calculate total
    total = sum(Decimal(str(item["price"])) * item["quantity"] for item in items)

    payload = {
        "client_id": invoice_data["client_id"],
        "invoice_number": invoice_data["invoice_number"],
        "date": str(invoice_data["date"]),
        "month": invoice_data["month"],
        "currency": invoice_data.get("currency", "MYR"),
        "type": invoice_data.get("type", "issuing"),
        "exchange_rate": str(Decimal(str(invoice_data.get("exchange_rate", 1.0)))),
        "total_amount": str(total),
    }

    result = supabase.table("invoices").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create invoice.")
    invoice = result.data[0]

    # Insert items
    for item in items:
        item_payload = {
            "invoice_id": invoice["id"],
            "description": item["description"],
            "price": str(Decimal(str(item["price"]))),
            "quantity": item["quantity"],
        }
        supabase.table("invoice_items").insert(item_payload).execute()

    if invoice_data.get("type") == "receiving":
        client = get_client(invoice["client_id"])
        if client:
            company_id = client["company_id"]
            # Trigger the auto-evaluation process in the background
            if background_tasks:
                background_tasks.add_task(evaluate_auto_payment, invoice["id"], invoice["client_id"], company_id)

    return get_invoice(invoice["id"])


def get_invoices(company_id: str) -> list[dict]:
    # Get clients for this company
    clients = get_clients(company_id)
    if not clients:
        return []

    client_ids = [c["id"] for c in clients]
    client_map = {c["id"]: c["name"] for c in clients}

    result = (
        supabase.table("invoices")
        .select("*")
        .in_("client_id", client_ids)
        .order("created_at", desc=True)
        .execute()
    )

    invoices = result.data
    for inv in invoices:
        inv["client_name"] = client_map.get(inv["client_id"], "Unknown")

    return invoices


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
    result = (
        supabase.table("invoices")
        .update({"status": status})
        .eq("id", invoice_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=400, detail="Database operation failed or returned no data.")
    return result.data[0]


def delete_invoice(invoice_id: str) -> bool:
    # Delete child items first to avoid FK constraint errors
    supabase.table("invoice_items").delete().eq("invoice_id", invoice_id).execute()
    supabase.table("invoices").delete().eq("id", invoice_id).execute()
    return True


# ═══════════════════════════════════════════
# Payments
# ═══════════════════════════════════════════
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

    if ai_decision.get("approve"):
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

