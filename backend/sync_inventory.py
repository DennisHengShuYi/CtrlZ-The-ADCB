import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from app.supabase_client import supabase

SEED_PRODUCTS = [
    {"name": "Curry Puff", "inventory": 120, "threshold": 30, "image": "🍛", "price": 4.50},
    {"name": "Roti Canai", "inventory": 85, "threshold": 20, "image": "🥞", "price": 2.50},
    {"name": "Onde-Onde", "inventory": 45, "threshold": 15, "image": "🍡", "price": 3.00},
    {"name": "Spicy Curry Puff", "inventory": 60, "threshold": 25, "image": "🌶️", "price": 5.00},
    {"name": "Kaya Puff", "inventory": 30, "threshold": 10, "image": "🥥", "price": 3.50},
]

def sync():
    print("Checking supabase DB...")
    
    try:
        # Get all companies
        companies = supabase.table("user_companies").select("id").execute().data
        if not companies:
            print("No companies found.")
            return

        c_id = companies[0]["id"]
        print(f"Using primary company_id: {c_id}")
        
        # update any existing ghost products to belong to the first company!
        resp = supabase.table("products").select("*").is_("company_id", "null").execute()
        ghost_prods = resp.data or []
        for gp in ghost_prods:
            supabase.table("products").update({"company_id": c_id, "price": 5.00}).eq("id", gp["id"]).execute()
            print(f"Updated ghost product {gp['name']}")
        
        # check if they have products
        prods = supabase.table("products").select("id").eq("company_id", c_id).execute().data
        if not prods:
            print(f"Seeding products for company {c_id}...")
            for seed in SEED_PRODUCTS:
                payload = dict(seed)
                payload["company_id"] = c_id
                supabase.table("products").insert(payload).execute()
            print("Mock data injected!")
            
        print("Inventory DB is now fully connected and synced!")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    sync()
