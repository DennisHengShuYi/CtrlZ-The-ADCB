
from decimal import Decimal
from app.supabase_client import supabase, save_prevet_result
from app.invoice_service import get_client

def create_dummy_tariff_invoice():
    client_id = "48aba8c8-7754-4df3-bdbf-a214235255dd"
    invoice_number = "INV-CROSS-BORDER-888"
    
    # 1. Check if exists
    existing = supabase.table("invoices").select("id").eq("invoice_number", invoice_number).execute()
    if existing.data:
        print(f"Dummy invoice {invoice_number} already exists. Cleaning up...")
        for inv in existing.data:
            supabase.table("invoice_items").delete().eq("invoice_id", inv["id"]).execute()
            supabase.table("invoices").delete().eq("id", inv["id"]).execute()

    # 2. Insert Invoice
    invoice_payload = {
        "client_id": client_id,
        "invoice_number": invoice_number,
        "date": "2024-03-12",
        "month": "2024-03",
        "currency": "USD",
        "type": "issuing",
        "exchange_rate": "4.75",
        "tariff": "50.00",
        "total_amount": "1050.00",
        "notes": "Dummy data for cross-border tariff testing"
    }
    
    res = supabase.table("invoices").insert(invoice_payload).execute()
    if not res.data:
        print("Failed to insert invoice")
        return
    
    invoice = res.data[0]
    invoice_id = invoice["id"]
    print(f"Created Invoice: {invoice_id}")

    # 3. Insert Items
    item_payload = {
        "invoice_id": invoice_id,
        "description": "Protective Gloves (Latex)",
        "price": "10.00",
        "quantity": 100,
        "unit": "pair",
        "origin_country": "CN"
    }
    supabase.table("invoice_items").insert(item_payload).execute()
    print("Created Invoice Items")

    # 4. Create a HITL Result (Approved)
    # This simulates an invoice that HAS gone through the workflow
    client = get_client(client_id)
    inv_dict = {
        "invoice_id": invoice_number,
        "invoice_date": "2024-03-12",
        "vendor": {"name": "Test Vendor", "address": "123 China Street", "country": "CN"},
        "buyer": {"name": client["name"], "address": client["address"], "country": "MY"},
        "line_items": [{
            "item_id": 1,
            "description": "Protective Gloves (Latex)",
            "quantity": 100,
            "unit": "pair",
            "unit_price": 10.0,
            "amount": 1000.0,
            "origin_country": "CN"
        }],
        "subtotal": 1000.0,
        "currency": "USD"
    }
    
    pre_vet = {
        "invoice_id": invoice_number,
        "line_items": [{
            "item_id": 1,
            "description": "Protective Gloves (Latex)",
            "quantity": 100,
            "unit": "pair",
            "unit_price": 10.0,
            "amount": 1000.0,
            "origin_country": "CN",
            "ahtn_code": "4015.11.0000",
            "ahtn_description": "Surgical Gloves",
            "tariff_rate": "5%",
            "tariff_amount": 50.0,
            "similarity": 0.95,
            "requires_hitl": True,
            "flags": []
        }],
        "total_tariff": 50.0,
        "currency": "USD",
        "any_requires_hitl": True,
        "all_flags": []
    }
    
    # Save as approved to show it's finished
    record_id = save_prevet_result(inv_dict, pre_vet, source_file="Dummy Seed")
    if record_id:
        supabase.table("invoice_prevet_results").update({
            "status": "approved",
            "reviewed_by": "system_seed"
        }).eq("id", record_id).execute()
        print(f"Created Approved HITL Record: {record_id}")

if __name__ == "__main__":
    create_dummy_tariff_invoice()
