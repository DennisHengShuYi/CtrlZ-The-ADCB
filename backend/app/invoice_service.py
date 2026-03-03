"""
Invoice Service — CRUD operations for invoices, clients, companies, payments.
Uses the Supabase client for all DB operations.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional

from app.supabase_client import supabase


# ═══════════════════════════════════════════
# Companies
# ═══════════════════════════════════════════
def create_company(user_id: str, data: dict) -> dict:
    payload = {**data, "user_id": user_id}
    result = supabase.table("user_companies").insert(payload).execute()
    return result.data[0] if result.data else {}


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
    return result.data[0] if result.data else {}


# ═══════════════════════════════════════════
# Clients
# ═══════════════════════════════════════════
def create_client(data: dict) -> dict:
    result = supabase.table("clients").insert(data).execute()
    return result.data[0] if result.data else {}


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


def get_client(client_id: str) -> Optional[dict]:
    result = (
        supabase.table("clients").select("*").eq("id", client_id).limit(1).execute()
    )
    return result.data[0] if result.data else None


def update_client(client_id: str, data: dict) -> dict:
    result = supabase.table("clients").update(data).eq("id", client_id).execute()
    return result.data[0] if result.data else {}


def delete_client(client_id: str) -> bool:
    supabase.table("clients").delete().eq("id", client_id).execute()
    return True


# ═══════════════════════════════════════════
# Invoices
# ═══════════════════════════════════════════
def create_invoice(invoice_data: dict, items: list[dict]) -> dict:
    # Calculate total
    total = sum(Decimal(str(item["price"])) * item["quantity"] for item in items)

    payload = {
        "client_id": invoice_data["client_id"],
        "invoice_number": invoice_data["invoice_number"],
        "date": str(invoice_data["date"]),
        "month": invoice_data["month"],
        "total_amount": float(total),
    }

    result = supabase.table("invoices").insert(payload).execute()
    invoice = result.data[0]

    # Insert items
    for item in items:
        item_payload = {
            "invoice_id": invoice["id"],
            "description": item["description"],
            "price": float(item["price"]),
            "quantity": item["quantity"],
        }
        supabase.table("invoice_items").insert(item_payload).execute()

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
    return result.data[0] if result.data else {}


def delete_invoice(invoice_id: str) -> bool:
    supabase.table("invoices").delete().eq("id", invoice_id).execute()
    return True


# ═══════════════════════════════════════════
# Payments
# ═══════════════════════════════════════════
def create_payment(data: dict) -> dict:
    payload = {
        "client_id": data["client_id"],
        "amount": float(data["amount"]),
        "date": str(data["date"]),
        "method": data.get("method"),
        "notes": data.get("notes"),
    }
    result = supabase.table("payments").insert(payload).execute()
    return result.data[0] if result.data else {}


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
        "total_invoiced": float(total_invoiced),
        "total_paid": float(total_paid),
        "net_balance": float(total_invoiced - total_paid),
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
    return result.data[0] if result.data else {}


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
