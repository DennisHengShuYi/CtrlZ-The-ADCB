"""
WhatsApp webhook routes — Agentic Order-to-Payment flow.
Receives messages, processes with AI, handles identity resolution,
smart inventory checks with auto-restock, and invoice generation.
"""

import json
import uuid
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, HTTPException

from app.auth import require_auth
from app.models import WhatsAppMessage
from app.ai_service import extract_invoice_data, generate_rejection_message
from app.currency_service import fetch_exchange_rate
from app.invoice_service import (
    get_company_with_fallback,
    get_client_by_name,
    get_client_by_phone,
    get_client,
    create_client,
    create_invoice,
    create_payment,
    create_pending_invoice,
    get_pending_invoice,
    delete_pending_invoice,
    get_product_by_name,
    update_product_inventory,
    adjust_product_inventory,
    get_financial_summary,
    update_invoice_status,
)
from app.supabase_client import supabase

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Country-to-currency mapping for personalization
COUNTRY_CURRENCY_MAP = {
    "MY": "MYR", "SG": "SGD", "ID": "IDR", "PH": "PHP",
    "TH": "THB", "VN": "VND", "US": "USD", "GB": "GBP",
    "AU": "AUD", "JP": "JPY", "KR": "KRW", "CN": "CNY",
    "IN": "INR", "AE": "AED", "SA": "SAR", "BN": "BND",
    "KH": "KHR", "LA": "LAK", "MM": "MMK",
}


def _generate_invoice_number() -> str:
    """Generate a sequential-style invoice number."""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:4].upper()
    return f"INV-{ts}-{short}"


def _normalize_date(raw: Any) -> str:
    """
    Safely parse AI-extracted date into ISO format (YYYY-MM-DD).
    Handles: "2026-03-09", "09", "03-09", "March 9", None, etc.
    Always returns a valid YYYY-MM-DD string.
    """
    today = date_type.today()
    if not raw or not str(raw).strip():
        return str(today)

    s = str(raw).strip()

    # Already ISO format
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        pass

    # Day only: "09" or "9"
    if s.isdigit() and len(s) <= 2:
        day = int(s)
        if 1 <= day <= 31:
            try:
                return str(today.replace(day=day))
            except ValueError:
                return str(today)

    # Month-day: "03-09" or "3-9"
    try:
        parsed = datetime.strptime(s, "%m-%d")
        return str(today.replace(month=parsed.month, day=parsed.day))
    except ValueError:
        pass

    # Try common formats
    for fmt in ("%B %d", "%b %d", "%d %B", "%d %b", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(s, fmt)
            if parsed.year == 1900:
                parsed = parsed.replace(year=today.year)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return str(today)


def _normalize_month(raw: Any, fallback_date: str) -> str:
    """
    Ensure month is in YYYY-MM format.
    Handles: "2026-03", "03", "March", None, etc.
    """
    today = date_type.today()
    if not raw or not str(raw).strip():
        return fallback_date[:7] if len(fallback_date) >= 7 else today.strftime("%Y-%m")

    s = str(raw).strip()

    # Already YYYY-MM
    if len(s) == 7 and s[4] == '-':
        try:
            int(s[:4])
            int(s[5:7])
            return s
        except ValueError:
            pass

    # Month number only: "03" or "3"
    if s.isdigit() and len(s) <= 2:
        month = int(s)
        if 1 <= month <= 12:
            return f"{today.year}-{month:02d}"

    # Month name: "March", "Mar"
    for fmt in ("%B", "%b"):
        try:
            parsed = datetime.strptime(s, fmt)
            return f"{today.year}-{parsed.month:02d}"
        except ValueError:
            continue

    return fallback_date[:7] if len(fallback_date) >= 7 else today.strftime("%Y-%m")


def _detect_currency_from_country(country_code: Optional[str], fallback: str = "MYR") -> str:
    """Detect the appropriate currency based on a buyer's country code."""
    if not country_code:
        return fallback
    return COUNTRY_CURRENCY_MAP.get(country_code.upper(), fallback)


def _resolve_or_create_buyer(
    company_id: str,
    phone_number: str,
    buyer_info: Optional[dict],
    client_name: Optional[str],
) -> Optional[dict]:
    """
    Step 1: Identity Resolution — look up buyer by phone or name.
    If not found and AI extracted buyer info, auto-create the buyer record.
    """
    # Try phone lookup first
    client = get_client_by_phone(company_id, phone_number)
    if client:
        return client

    # Try name lookup
    name = None
    if buyer_info and buyer_info.get("name"):
        name = buyer_info["name"]
    elif client_name:
        name = client_name

    if name:
        client = get_client_by_name(company_id, name)
        if client:
            return client

    # Auto-create buyer from AI-extracted data
    if name:
        new_client_data = {
            "company_id": company_id,
            "name": name,
            "phone_number": phone_number,
            "type": "customer",
        }
        if buyer_info:
            if buyer_info.get("address"):
                new_client_data["address"] = buyer_info["address"]
            if buyer_info.get("country"):
                new_client_data["country"] = buyer_info["country"]

        result = create_client(new_client_data)
        result["_just_created"] = True
        return result

    return None


async def _smart_inventory_check(
    company_id: str,
    items: list[dict],
    base_currency: str,
) -> tuple[list[dict], list[str], list[dict]]:
    """
    Step 2: Smart Inventory Check with Financial Buffer Check.
    For each item, match to a product. If stock would drop below threshold:
      1. Check financial buffer (get_financial_summary)
      2. Create a supplier "Receiving" invoice
      3. Simulate a payment for the supplier order (Agentic Auto-Pay)
      4. Update inventory

    Returns:
        (restock_invoices, agent_steps, insufficient_items) — list of created restock invoices,
        log steps, and items that remain insufficient after restock attempts.
    """
    agent_steps = []
    restock_invoices = []
    insufficient_items = []

    # Pre-fetch financial summary once for all items
    financial_summary = get_financial_summary(company_id)
    cash_on_hand = Decimal(str(financial_summary["cash_on_hand"]))
    available_for_expenses = Decimal(str(financial_summary["available_for_expenses"]))
    running_spend = Decimal("0")  # Track cumulative spend within this agentic cycle

    for item in items:
        description = item.get("description", "")
        requested_qty = item.get("quantity", 0)

        product = get_product_by_name(company_id, description)
        if not product:
            agent_steps.append(f"Product '{description}' not found in inventory — rejecting item")
            insufficient_items.append({
                "description": description,
                "requested": requested_qty,
                "available": 0,
                "reason": "product not found"
            })
            continue

        current_inventory = product.get("inventory", 0)
        threshold = product.get("threshold", 10)
        remaining = current_inventory - requested_qty

        if remaining >= threshold:
            agent_steps.append(f"Stock OK ({description}): {current_inventory} -> {remaining} (threshold: {threshold})")
            continue

        # --- Restock Triggered ---
        supplier_id = product.get("supplier_id")
        cost_price = float(product.get("cost_price", 0)) or float(product.get("price", 0))
        product_unit = product.get("unit") or item.get("unit", "pcs")
        product_origin = product.get("origin_country") or item.get("origin_country")

        # Calculate restock amount: enough to fill back to threshold + buffer
        restock_amount = max(threshold * 5, requested_qty * 2)

        agent_steps.append(
            f"Stock Low ({description}): {current_inventory} - {requested_qty} = {remaining} < {threshold}. "
            f"Triggered Supplier Order for {restock_amount}{product_unit}"
        )

        if not supplier_id:
            agent_steps.append(f"WARNING: No supplier linked for '{description}' — cannot auto-restock")
            insufficient_items.append({"description": description, "requested": requested_qty, "available": current_inventory, "reason": "no supplier linked"})
            continue

        # Get supplier info
        supplier = get_client(supplier_id)
        if not supplier:
            agent_steps.append(f"WARNING: Supplier ID {supplier_id} not found")
            insufficient_items.append({"description": description, "requested": requested_qty, "available": current_inventory, "reason": "supplier not found"})
            continue

        supplier_currency = product.get("currency", base_currency)

        # Calculate exchange rate if currencies differ
        exchange_rate = Decimal("1.0")
        if supplier_currency != base_currency:
            try:
                exchange_rate = await fetch_exchange_rate(supplier_currency, base_currency)
            except Exception as e:
                agent_steps.append(f"Exchange rate fetch failed ({supplier_currency}->{base_currency}): {e}")

        # --- Financial Buffer Check ---
        restock_cost = Decimal(str(cost_price)) * restock_amount
        restock_cost_base = restock_cost * exchange_rate
        remaining_budget = available_for_expenses - running_spend

        if restock_cost_base > cash_on_hand:
            agent_steps.append(
                f"RESTOCK BLOCKED ({description}): Cost {restock_cost_base} {base_currency} exceeds "
                f"cash on hand {cash_on_hand} {base_currency} — skipping"
            )
            insufficient_items.append({"description": description, "requested": requested_qty, "available": current_inventory, "reason": "insufficient cash on hand"})
            continue

        if restock_cost_base > remaining_budget:
            # Reduce restock amount to fit budget
            affordable_qty = int(float(remaining_budget / (Decimal(str(cost_price)) * exchange_rate)))
            if affordable_qty <= 0:
                agent_steps.append(
                    f"RESTOCK BLOCKED ({description}): Insufficient budget "
                    f"(available: {remaining_budget} {base_currency}) — skipping"
                )
                insufficient_items.append({"description": description, "requested": requested_qty, "available": current_inventory, "reason": "insufficient budget"})
                continue
            agent_steps.append(
                f"Budget constrained ({description}): Reduced restock from {restock_amount} to {affordable_qty} "
                f"to fit available budget of {remaining_budget} {base_currency}"
            )
            restock_amount = affordable_qty
            restock_cost = Decimal(str(cost_price)) * restock_amount
            restock_cost_base = restock_cost * exchange_rate

        # Create a "Receiving" invoice (restock from supplier)
        restock_invoice_number = _generate_invoice_number()
        today = str(date_type.today())
        month = date_type.today().strftime("%Y-%m")

        restock_invoice_data = {
            "client_id": supplier_id,
            "invoice_number": restock_invoice_number,
            "date": today,
            "month": month,
            "currency": supplier_currency,
            "type": "receiving",
            "exchange_rate": str(exchange_rate),
            "notes": f"Auto-restock triggered for {description}",
        }

        restock_items = [{
            "description": description,
            "price": cost_price,
            "quantity": restock_amount,
            "unit": product_unit,
            "origin_country": product_origin,
            "unit_price": cost_price,
        }]

        # create_invoice with type="receiving" automatically increments inventory
        restock_invoice = create_invoice(restock_invoice_data, restock_items)
        if not restock_invoice:
            agent_steps.append(f"WARNING: Failed to create restock invoice for {description} (PGRST204)")
            insufficient_items.append({"description": description, "requested": requested_qty, "available": current_inventory, "reason": "restock invoice creation failed"})
            continue

        restock_invoices.append(restock_invoice)

        # --- Simulated Supplier Payment (Agentic Auto-Pay) ---
        try:
            payment_payload = {
                "client_id": supplier_id,
                "amount": str(restock_cost),
                "date": today,
                "method": "Agentic Auto-Pay",
                "notes": f"Auto-restock payment for {restock_amount}{product_unit} {description}",
                "currency": supplier_currency,
                "exchange_rate": str(exchange_rate),
            }
            create_payment(payment_payload)
            update_invoice_status(restock_invoice["id"], "paid")
            running_spend += restock_cost_base

            agent_steps.append(
                f"Supplier Payment: {restock_cost} {supplier_currency} paid to {supplier.get('name', 'Supplier')} "
                f"(Invoice {restock_invoice_number} marked paid)"
            )
        except Exception as e:
            agent_steps.append(f"WARNING: Supplier payment failed for {restock_invoice_number}: {e}")

        # Inventory was already incremented by create_invoice (type=receiving)
        new_inventory = current_inventory + restock_amount
        agent_steps.append(
            f"Restock Complete: {restock_amount}{product_unit} {description} added to inventory "
            f"(was {current_inventory}, now {new_inventory}). Invoice: {restock_invoice_number}"
        )

    return restock_invoices, agent_steps, insufficient_items


@router.post("/webhook")
async def whatsapp_webhook(
    body: WhatsAppMessage,
    background_tasks: BackgroundTasks,
    claims: dict[str, Any] = Depends(require_auth),
):
    """
    Agentic Order-to-Payment Flow:
    1. Extract structured data with AI (vendor, buyer, line_items with units)
    2. Identity Resolution — find or auto-create buyer
    3. Smart Inventory Check — auto-restock if below threshold (with financial checks)
    4. Generate final Customer Invoice with personalized currency
    5. Deduct sold quantities from inventory
    6. Return chain-of-thought agent_steps for debugging
    """
    user_id = claims.get("sub", "")
    company = await get_company_with_fallback(user_id)
    if not company:
        return {
            "status": "error",
            "message": "Please set up your company profile first.",
        }

    company_id = company["id"]
    base_currency = company.get("base_currency", "MYR")
    agent_steps = []

    # ── Step 0: AI Extraction ──
    result = await extract_invoice_data(body.message)

    if result.get("status") == "error":
        return {
            "status": "error",
            "message": result.get("questions", ["An error occurred."])[0],
        }

    if result["status"] == "incomplete":
        data = result.get("data", {})
        questions = result.get("questions", [])
        missing = [k for k, v in data.items() if v is None or v == []]

        create_pending_invoice(
            user_id=user_id,
            raw_message=body.message,
            extracted_data=data,
            missing_fields=missing,
        )

        return {
            "status": "incomplete",
            "questions": questions,
            "extracted_data": data,
        }

    # ── Status == "complete" ──
    data = result["data"]
    items = data.get("items", [])
    vendor_info = data.get("vendor")
    buyer_info = data.get("buyer")
    client_name = data.get("client_name")
    notes = data.get("notes")

    # Determine buyer name and country for logging + currency personalization
    buyer_display = (buyer_info or {}).get("name") or client_name or "Unknown"
    buyer_country = (buyer_info or {}).get("country", "")
    agent_steps.append(f"Detected Order for {buyer_display}" + (f" ({buyer_country})" if buyer_country else ""))

    # ── Step 1: Identity Resolution ──
    client = _resolve_or_create_buyer(company_id, body.phone_number, buyer_info, client_name)

    if not client:
        return {
            "status": "client_not_found",
            "message": f"Could not identify buyer '{buyer_display}'. Please provide a buyer name.",
            "extracted_data": data,
            "agent_steps": agent_steps,
        }

    # Use resolved client name for personalized greetings
    buyer_display = client.get("name") or buyer_display

    if client.get("_just_created"):
        agent_steps.append(f"Auto-created new customer: {client['name']}")
    else:
        agent_steps.append(f"Resolved buyer: {client['name']} (ID: {client['id'][:8]}...)")

    # ── Step 2: Smart Inventory Check + Auto-Restock ──
    restock_invoices, inventory_steps, insufficient_items = await _smart_inventory_check(
        company_id, items, base_currency
    )
    agent_steps.extend(inventory_steps)

    # ── Step 2b: Reject if items are insufficient after restock attempts ──
    if insufficient_items:
        rejection_message = await generate_rejection_message(insufficient_items, buyer_display)
        agent_steps.append(f"Order REJECTED: {len(insufficient_items)} item(s) unavailable — skipping invoice creation")
        print(json.dumps({"agent_steps": agent_steps}, indent=2))
        return {
            "status": "rejected",
            "reply": rejection_message,
            "message": rejection_message,
            "insufficient_items": insufficient_items,
            "restock_invoices": restock_invoices,
            "agent_steps": agent_steps,
        }

    # ── Step 3: Generate Final Customer Invoice ──

    # 3a. Determine invoice currency FIRST (before pricing)
    invoice_currency = data.get("currency", "MYR")
    effective_country = buyer_country or client.get("country")
    client_country = client.get("country")
    if client_country:
        client_currency = _detect_currency_from_country(client_country)
        if client_currency != base_currency:
            invoice_currency = client_currency
            agent_steps.append(f"Currency set to {invoice_currency} from client profile (country: {client_country})")
    elif effective_country and invoice_currency == "MYR":
        detected_currency = _detect_currency_from_country(effective_country)
        if detected_currency != "MYR":
            invoice_currency = detected_currency
            agent_steps.append(f"Currency personalized to {invoice_currency} based on buyer location ({effective_country})")

    # 3b. Fetch exchange rate if currency differs from base
    exchange_rate = Decimal("1.0")
    if invoice_currency != base_currency:
        try:
            exchange_rate = await fetch_exchange_rate(invoice_currency, base_currency)
            agent_steps.append(f"Exchange rate: 1 {invoice_currency} = {exchange_rate} {base_currency}")
        except Exception as e:
            agent_steps.append(f"Exchange rate lookup failed: {e}")

    # 3c. Resolve item prices — convert from base currency to invoice currency
    for item in items:
        # Fill origin_country from product if not AI-detected
        if not item.get("origin_country"):
            product = get_product_by_name(company_id, item["description"])
            if product and product.get("origin_country"):
                item["origin_country"] = product["origin_country"]

        if item.get("price") is None:
            product = get_product_by_name(company_id, item["description"])
            base_price = float(product.get("price", 0)) if product else 0

            # Convert base_currency price → invoice_currency price
            if invoice_currency != base_currency and float(exchange_rate) > 0:
                item_price = round(base_price / float(exchange_rate), 2)
                agent_steps.append(
                    f"Converted {item.get('description')}: {base_price} {base_currency} → {item_price} {invoice_currency} (rate: {exchange_rate})"
                )
            else:
                item_price = base_price

            item["price"] = item_price
            item["unit_price"] = item_price
        else:
            # AI provided a price — ensure unit_price is set
            if item.get("unit_price") is None:
                item["unit_price"] = float(item["price"])

    invoice_number = _generate_invoice_number()
    invoice_date = _normalize_date(data.get("date"))
    month = _normalize_month(data.get("month"), invoice_date)

    invoice_data = {
        "client_id": client["id"],
        "invoice_number": invoice_number,
        "date": invoice_date,
        "month": month,
        "currency": invoice_currency,
        "type": "issuing",
        "exchange_rate": str(exchange_rate),
        "notes": (notes + " (Order via WhatsApp)") if notes else "Order via WhatsApp",
        "tariff": 0,
    }

    # create_invoice with type="issuing" automatically decrements inventory
    invoice = create_invoice(invoice_data, items, background_tasks, save_items=True)

    if not invoice:
        agent_steps.append("ERROR: Failed to create customer invoice (PGRST204)")
        print(json.dumps({"agent_steps": agent_steps}, indent=2))
        return {
            "status": "error",
            "message": "Failed to create customer invoice. Please try again.",
            "agent_steps": agent_steps,
        }

    # Log final inventory state for each item
    for item in items:
        product = get_product_by_name(company_id, item["description"])
        if product:
            agent_steps.append(
                f"Inventory synced ({item['description']}): stock is now {product['inventory']}"
            )

    agent_steps.append(f"Issuing Customer Invoice: {invoice_number}")

    # Clean up pending invoices
    pending = get_pending_invoice(user_id)
    if pending:
        delete_pending_invoice(pending["id"])

    # ── Visual Debugging Output (Terminal) ──
    print(json.dumps({"agent_steps": agent_steps}, indent=2))

    # ── Build Flattened Response Payload ──
    vendor_payload = {
        "name": company.get("name"),
        "address": company.get("address", ""),
        "country": company.get("country", "MY"),
    }

    buyer_payload = {
        "name": client.get("name"),
        "address": client.get("address", ""),
        "country": client.get("country", ""),
    }

    formatted_items = []
    subtotal = 0.0
    for idx, item in enumerate(items, start=1):
        qty = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0.0)
        amount = float(qty) * float(unit_price)
        subtotal += amount
        formatted_items.append({
            "item_id": idx,
            "description": item.get("description", ""),
            "quantity": qty,
            "unit": item.get("unit", "pcs"),
            "unit_price": unit_price,
            "amount": round(amount, 2),
            "origin_country": item.get("origin_country", ""),
        })

    return {
        # Required for Frontend UI
        "status": "complete",
        "reply": f"Invoice {invoice_number} created successfully!",
        "message": f"Invoice {invoice_number} created successfully!",
        "action_type": "text",
        # Flattened Data Structure
        "invoice_id": invoice_number,
        "invoice_date": invoice_date,
        "vendor": vendor_payload,
        "buyer": buyer_payload,
        "line_items": formatted_items,
        "subtotal": round(subtotal, 2),
        "currency": invoice_currency,
        "notes": notes or "Test invoice in pre-vet format",
        "restock_invoices": restock_invoices,
        "agent_steps": agent_steps,
    }

# ──────────────────────────────────────
# Unified Agentic Interface (Frontend Sandbox)
# ──────────────────────────────────────

@router.post("/unified")
async def unified_webhook(
    background_tasks: BackgroundTasks,
    message: str = Form(""),
    sender_phone: str = Form("web-ui-unified"),
    file: Optional[UploadFile] = File(None),
    claims: dict[str, Any] = Depends(require_auth),
):
    """
    Experimental 'Unified' entry point from the sandbox UI.
    Supports both text messages and file uploads (receipts/invoices).
    """
    user_id = claims.get("sub", "")
    company = await get_company_with_fallback(user_id)
    if not company:
        return {"status": "error", "message": "Company not found."}

    company_id = company["id"]
    base_currency = company.get("base_currency", "MYR")
    agent_steps = []

    # 1. Handle File Upload if present
    if file:
        agent_steps.append(f"Received file: {file.filename} ({file.content_type})")
        content = await file.read()
        
        # Classify and process file
        from app.ai_service import classify_media_intent, extract_receipt_data, extract_supplier_invoice_v2
        from app.invoice_service import match_receipt_to_invoice, process_payment_verification
        
        classification = await classify_media_intent(content, file.content_type)
        dtype = classification.get("detected_type", "IRRELEVANT")
        agent_steps.append(f"AI Classification: {dtype}")

        if dtype == "CUSTOMER_RECEIPT":
            # Extract detailed receipt data
            receipt_data = await extract_receipt_data(content, file.content_type)
            agent_steps.append(f"Extracted Receipt: {receipt_data.get('amount')} {receipt_data.get('currency')}")
            
            # Find matching invoice
            matches = match_receipt_to_invoice(company_id, receipt_data)
            if matches:
                invoice = matches[0]
                agent_steps.append(f"Found Match: Invoice {invoice['invoice_number']} (Score: {invoice.get('match_score')})")
                
                # Verify and process
                payment_data = {
                    "client_id": invoice["client_id"],
                    "invoice_id": invoice["id"],
                    "amount": receipt_data["amount"],
                    "date": receipt_data.get("transaction_date") or str(date_type.today()),
                    "currency": receipt_data.get("currency", "MYR"),
                }
                process_payment_verification(company_id, payment_data)
                agent_steps.append(f"Verification Successful: Invoice {invoice['invoice_number']} marked as PAID.")
                
                return {
                    "status": "complete",
                    "action_type": "receipt_matched",
                    "reply": f"Processing Receipt... Match Found! Invoice {invoice['invoice_number']} for {invoice['client_name']} is now paid.",
                    "invoice_number": invoice["invoice_number"],
                    "agent_steps": agent_steps
                }
            else:
                return {
                    "status": "error",
                    "reply": "I received the receipt but couldn't find a matching unpaid invoice in your finance records.",
                    "agent_steps": agent_steps
                }

        elif dtype == "SUPPLIER_INVOICE":
            # Extract detailed supplier invoice
            inv_v2 = await extract_supplier_invoice_v2(content, file.content_type)
            supplier_name = inv_v2.get("vendor", {}).get("name", "Unknown Supplier")
            bill_amount = float(inv_v2.get("amount", 0))
            bill_currency = inv_v2.get("currency", "MYR")
            agent_steps.append(f"Extracted Supplier Bill: {bill_amount} {bill_currency} from {supplier_name}")

            # Financial evaluation before creating invoice
            from app.ai_service import evaluate_supplier_bill
            financial_summary = get_financial_summary(company_id)
            cash_on_hand = float(financial_summary.get("cash_on_hand", 0))
            available_for_expenses = float(financial_summary.get("available_for_expenses", 0))
            agent_steps.append(f"Financial Check: Cash={cash_on_hand} {base_currency}, Available={available_for_expenses} {base_currency}")

            evaluation = await evaluate_supplier_bill(
                amount=bill_amount,
                currency=bill_currency,
                description=f"Supplier invoice from {supplier_name}",
                supplier_name=supplier_name,
                cash_on_hand=cash_on_hand,
                available_for_expenses=available_for_expenses,
                base_currency=base_currency,
                line_items=inv_v2.get("line_items", []),
            )
            decision = evaluation.get("decision", "defer")
            agent_steps.append(f"AI Decision: {decision} — {evaluation.get('reason', '')}")

            # Create a 'receiving' invoice
            invoice_data = {
                "client_id": None,
                "invoice_number": inv_v2.get("reference_number") or _generate_invoice_number(),
                "date": inv_v2.get("transaction_date") or str(date_type.today()),
                "month": (inv_v2.get("transaction_date") or str(date_type.today()))[:7],
                "currency": bill_currency,
                "type": "receiving",
            }

            # Resolve supplier
            supplier = _resolve_or_create_buyer(company_id, sender_phone, inv_v2.get("vendor"), None)
            if not supplier:
                return {"status": "error", "reply": "Could not identify supplier on this bill.", "agent_steps": agent_steps}

            invoice_data["client_id"] = supplier["id"]
            invoice = create_invoice(invoice_data, inv_v2.get("line_items", []), background_tasks)
            agent_steps.append(f"Supplier Invoice Tracked: {invoice['invoice_number']}")

            if decision == "negotiate":
                negotiation_msg = evaluation.get("negotiation_message") or "We'd like to discuss adjusted terms."
                agent_steps.append(f"Negotiation recommended: {negotiation_msg}")
                return {
                    "status": "complete",
                    "action_type": "supplier_invoice_negotiate",
                    "reply": f"Supplier invoice from {supplier_name} for {bill_amount} {bill_currency} recorded.\n\n[!] {evaluation.get('reason', 'Budget is tight.')}\n\nRecommended counter-offer:\n{negotiation_msg}",
                    "invoice_number": invoice["invoice_number"],
                    "invoice": invoice,
                    "evaluation": evaluation,
                    "agent_steps": agent_steps,
                }
            elif decision == "defer":
                agent_steps.append("Payment deferred — insufficient funds")
                return {
                    "status": "complete",
                    "action_type": "supplier_invoice_negotiate",
                    "reply": f"Supplier invoice from {supplier_name} for {bill_amount} {bill_currency} recorded.\n\n[x] {evaluation.get('reason', 'Insufficient funds to pay this bill.')}\n\nPayment has been deferred. Please review your cash flow before proceeding.",
                    "invoice_number": invoice["invoice_number"],
                    "invoice": invoice,
                    "evaluation": evaluation,
                    "agent_steps": agent_steps,
                }
            else:
                agent_steps.append("Auto-approved for payment")
                return {
                    "status": "complete",
                    "action_type": "supplier_invoice_approved",
                    "reply": f"Supplier invoice from {supplier_name} for {bill_amount} {bill_currency} recorded.\n\n[v] {evaluation.get('reason', 'Finances are healthy.')}\n\nThis bill has been auto-approved for payment.",
                    "invoice_number": invoice["invoice_number"],
                    "invoice": invoice,
                    "evaluation": evaluation,
                    "agent_steps": agent_steps,
                }

        else:
            return {"status": "error", "reply": "I couldn't identify this as a receipt or supplier invoice.", "agent_steps": agent_steps}

    # 2. Handle Text Message
    if message:
        # Re-use the existing agentic flow logic from whatsapp_webhook
        # (For simplicity in this sandbox, we wrap the body)
        msg_body = WhatsAppMessage(phone_number=sender_phone, message=message)
        return await whatsapp_webhook(msg_body, background_tasks, claims)

    return {"status": "error", "message": "Nothing to process."}


@router.delete("/unified/session")
async def reset_session(
    sender_phone: str = "web-ui-unified",
    claims: dict[str, Any] = Depends(require_auth)
):
    """Reset session / pending invoices for this user."""
    user_id = claims.get("sub", "")
    pending = get_pending_invoice(user_id)
    if pending:
        delete_pending_invoice(pending["id"])
    return {"status": "success", "message": "Session reset."}
