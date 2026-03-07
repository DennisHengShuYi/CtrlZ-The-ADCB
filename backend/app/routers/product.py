import os
from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

from app.supabase_client import supabase
from app.auth import require_auth
from app.invoice_service import get_company

env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

router = APIRouter(prefix="/api/products", tags=["products"])

# Static seed data (your mock products) - removed seeding to prevent resetting company_id
# If you want to use it, you'd need to associate with a specific company_id now.

# --- Pydantic models ---
class ProductBase(BaseModel):
    name: str
    inventory: int
    threshold: int
    image: Optional[str] = None
    price: Optional[float] = 0.0
    cost_price: Optional[float] = 0.0
    currency: Optional[str] = "MYR"
    company_id: Optional[str] = None
    supplier_id: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    inventory: Optional[int] = None
    threshold: Optional[int] = None
    image: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    currency: Optional[str] = None
    supplier_id: Optional[str] = None

class Product(ProductBase):
    id: str

class TopProduct(Product):
    score: int
    inquiries: int

class MostEnquired(BaseModel):
    name: str
    inquiries: int


# --- Helper: compute scores (same logic as before, using DB product names) ---
def get_all_instagram_posts():
    if not supabase:
        return []
    try:
        resp = supabase.table("instagram_posts").select("*").execute()
        return resp.data
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return []

def get_all_whatsapp_messages():
    if not supabase:
        return []
    try:
        resp = supabase.table("whatsapp_messages") \
            .select("content, intent") \
            .eq("role", "user") \
            .execute()
        return resp.data
    except Exception as e:
        print(f"Error fetching whatsapp messages: {e}")
        return []

def count_mentions_in_text(text: str, product_name: str) -> bool:
    return product_name.lower() in text.lower()

def compute_product_scores(products):
    if not products:
        return {}, {}

    posts = get_all_instagram_posts()
    whatsapp_msgs = get_all_whatsapp_messages()

    product_scores = {p["name"]: 0 for p in products}
    product_inquiries = {p["name"]: 0 for p in products}

    # Process Instagram posts
    for post in posts:
        caption = post.get("caption", "")
        mentioned = [p["name"] for p in products if count_mentions_in_text(caption, p["name"])]
        if not mentioned:
            continue
        likes = post.get("likes_count", 0)
        comments_count = post.get("comments_count", 0)
        for prod in mentioned:
            product_scores[prod] += likes * 1
            product_scores[prod] += comments_count * 2

    # Process WhatsApp messages
    for msg in whatsapp_msgs:
        content = msg.get("content", "")
        intent = msg.get("intent", "")
        if intent not in ["order", "interest"]:
            continue
        for prod in products:
            if count_mentions_in_text(content, prod["name"]):
                product_scores[prod["name"]] += 3
                product_inquiries[prod["name"]] += 1

    return product_scores, product_inquiries


# --- Endpoints ---

@router.get("", response_model=List[Product])
async def get_products(claims: dict[str, Any] = Depends(require_auth)):
    """Return all products for the current user's company."""
    if not supabase:
        return []
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        return []
    
    resp = supabase.table("products").select("*").eq("company_id", company["id"]).execute()
    return [Product(**p) for p in resp.data]

@router.get("/top", response_model=List[TopProduct])
async def get_top_products(limit: int = 5, claims: dict[str, Any] = Depends(require_auth)):
    """Return top products by weighted score, including inventory and inquiry count."""
    if not supabase:
        return []
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        return []

    resp = supabase.table("products").select("*").eq("company_id", company["id"]).execute()
    products = resp.data
    if not products:
        return []
    
    scores, inquiries = compute_product_scores(products)
    result = []
    for prod in products:
        result.append({
            **prod,
            "score": scores.get(prod["name"], 0),
            "inquiries": inquiries.get(prod["name"], 0)
        })
    result.sort(key=lambda x: x["score"], reverse=True)
    return result[:limit]

@router.get("/most-enquired", response_model=MostEnquired)
async def get_most_enquired_product(claims: dict[str, Any] = Depends(require_auth)):
    """Return the product with the highest WhatsApp inquiry count."""
    if not supabase:
         return {"name": "None", "inquiries": 0}
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        return {"name": "None", "inquiries": 0}

    resp = supabase.table("products").select("*").eq("company_id", company["id"]).execute()
    products = resp.data
    _, inquiries = compute_product_scores(products)
    if not inquiries:
        return {"name": "None", "inquiries": 0}
    max_name = max(inquiries.items(), key=lambda x: x[1])[0]
    return {"name": max_name, "inquiries": inquiries[max_name]}

@router.post("", response_model=Product)
async def create_product(product: ProductCreate, claims: dict[str, Any] = Depends(require_auth)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    user_id = claims.get("sub", "")
    company = get_company(user_id)
    if not company:
        raise HTTPException(status_code=400, detail="Company not found")

    payload = product.dict(exclude_none=True)
    payload["company_id"] = company["id"]

    try:
        resp = supabase.table("products").insert(payload).execute()
        return Product(**resp.data[0])
    except Exception as e:
        print(f"Create err: {e}")
        raise HTTPException(status_code=500, detail="Failed to create product")


@router.patch("/{product_id}", response_model=Product)
async def update_product(product_id: str, updates: ProductUpdate, claims: dict[str, Any] = Depends(require_auth)):
    """Update inventory, threshold, price, etc. of a product."""
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")

    # Build update dict, excluding None values
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Add updated_at timestamp
    update_data["updated_at"] = datetime.utcnow().isoformat()

    try:
        resp = supabase.table("products").update(update_data).eq("id", product_id).execute()
        if not resp.data:
            raise HTTPException(status_code=404, detail="Product not found")
        return Product(**resp.data[0])
    except Exception as e:
        print(f"Update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update product")

@router.delete("/{product_id}")
async def delete_product(product_id: str, claims: dict[str, Any] = Depends(require_auth)):
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        supabase.table("products").delete().eq("id", product_id).execute()
        return {"status": "success"}
    except Exception as e:
        print(f"Delete err: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete product")