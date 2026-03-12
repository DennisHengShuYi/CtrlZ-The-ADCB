import os
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

# Load environment variables from the project root
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("[v] Instagram: Gemini client initialized")
    except Exception as e:
        print(f"[x] Instagram: Failed to initialize Gemini client: {e}")
        client = None
else:
    print("[!] Instagram: No Gemini API key found, using fallback only")
    client = None

# Import shared Supabase client
from app.supabase_client import supabase

USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
if USE_SUPABASE:
    try:
        supabase.table("instagram_comments").select("*").limit(1).execute()
        print("[v] Instagram: Supabase connected")
    except Exception as e:
        print(f"[x] Instagram: Supabase connection failed: {e}")
        supabase = None
else:
    supabase = None

# Import Clerk auth dependency (adjust if needed)
from app.auth import require_auth

router = APIRouter(prefix="/api/instagram", tags=["instagram"])

# --- Pydantic models ---
class Comment(BaseModel):
    id: str
    username: str
    text: str
    sentiment: Optional[str] = None  # may be stored in DB

class Post(BaseModel):
    id: str
    caption: str
    likes: int
    comments: List[Comment]

class CommentAnalysis(BaseModel):
    sentiment: str  # positive/negative/neutral
    suggested_reply: str
    product_mentioned: Optional[str] = None

class PostEngagement(BaseModel):
    post_id: str
    total_likes: int
    total_comments: int
    top_products: List[str]
    engagement_score: int

# --- Sample data for seeding (only used if tables are empty) ---
SAMPLE_POSTS = [
    {
        "id": "post1",
        "caption": "New curry puffs! Try our spicy variant 🔥",
        "likes_count": 120,
        "comments": [
            {"id": "c1", "username": "user1", "text": "Looks delicious!"},
            {"id": "c2", "username": "user2", "text": "How much for 50 boxes?"},
            {"id": "c3", "username": "user3", "text": "Expensive la 😕"},
        ]
    },
    {
        "id": "post2",
        "caption": "Roti canai frozen – just heat and eat!",
        "likes_count": 85,
        "comments": [
            {"id": "c4", "username": "user4", "text": "Where to buy?"},
            {"id": "c5", "username": "user5", "text": "Sedap! I want 10 packs"},
        ]
    }
]

# --- Initialize Instagram posts in Supabase (if empty) ---
def init_instagram_posts():
    if not USE_SUPABASE or not supabase:
        return
    try:
        existing = supabase.table("instagram_posts").select("id").limit(1).execute()
        if not existing.data:
            for post in SAMPLE_POSTS:
                # Insert post
                supabase.table("instagram_posts").insert({
                    "id": post["id"],
                    "caption": post["caption"],
                    "likes_count": post["likes_count"],
                    "comments_count": len(post["comments"])
                }).execute()
                # Insert its comments
                for comment in post["comments"]:
                    supabase.table("instagram_comments").insert({
                        "id": comment["id"],
                        "post_id": post["id"],
                        "username": comment["username"],
                        "text": comment["text"],
                        "sentiment": None,
                        "ai_reply": None
                    }).execute()
            print("[v] Instagram: Sample posts and comments stored in Supabase")
    except Exception as e:
        print(f"[x] Instagram: Failed to store sample posts: {e}")

# Call it at module load
init_instagram_posts()

# --- Helper: retrieve product information from Instagram posts ---
def get_product_info_from_posts(keywords: Optional[List[str]] = None) -> str:
    """
    Fetch Instagram post captions from Supabase.
    If keywords provided, return only those matching any keyword.
    Otherwise return all posts.
    """
    if not USE_SUPABASE or not supabase:
        return ""
    try:
        response = supabase.table("instagram_posts").select("caption").execute()
        posts = response.data
        if not posts:
            return ""

        if keywords:
            relevant = []
            for post in posts:
                caption = post["caption"].lower()
                if any(kw.lower() in caption for kw in keywords):
                    relevant.append(f"- {post['caption']}")
            if relevant:
                return "Relevant product info from Instagram:\n" + "\n".join(relevant)
            return ""
        else:
            # Return all posts
            all_captions = "\n".join([f"- {p['caption']}" for p in posts])
            return f"Our products (from Instagram):\n{all_captions}"
    except Exception as e:
        print(f"Error fetching product info: {e}")
        return ""

# --- Helper: analyze comment with Gemini (unchanged) ---
def analyze_comment_with_gemini(comment_text: str, post_caption: str) -> dict:
    if not client:
        # Fallback logic if Gemini not available
        sentiment = "neutral"
        suggested_reply = "Thanks for your comment! Let us know if you have any questions."
        product_mentioned = None
        return {"sentiment": sentiment, "suggested_reply": suggested_reply, "product_mentioned": product_mentioned}

    # Fetch product info to enrich context
    product_info = get_product_info_from_posts()  # get all products

    prompt = f"""
{product_info}

Analyze this Instagram comment on a food business post.
Post caption: "{post_caption}"
Comment: "{comment_text}"

Return JSON with:
- sentiment: one of "positive", "neutral", "negative"
- suggested_reply: a friendly, appropriate reply (if negative, apologetic and helpful; if positive, thank them; if neutral, offer more info)
- product_mentioned: any product name mentioned (or null)

Reply ONLY with JSON, no other text.
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        raw = response.text.strip()
        if raw.startswith("```json"):
            raw = raw[7:-3]
        elif raw.startswith("```"):
            raw = raw[3:-3]
        return json.loads(raw)
    except Exception as e:
        print(f"Gemini analysis error: {e}, using fallback")
        return {
            "sentiment": "neutral",
            "suggested_reply": "Thanks for your feedback! We'll get back to you soon.",
            "product_mentioned": None
        }

# --- Endpoints ---

@router.get("/feed", response_model=List[Post])
async def get_feed():
    """Return Instagram posts with their comments from Supabase."""
    if not supabase:
        return []  # fallback empty list

    try:
        # Fetch all posts
        posts_resp = supabase.table("instagram_posts").select("*").execute()
        posts_data = posts_resp.data or []

        # Fetch all comments
        comments_resp = supabase.table("instagram_comments").select("*").execute()
        comments_data = comments_resp.data or []

        # Group comments by post_id
        comments_by_post = {}
        for c in comments_data:
            post_id = c.get("post_id")
            if post_id not in comments_by_post:
                comments_by_post[post_id] = []
            comments_by_post[post_id].append({
                "id": c["id"],
                "username": c["username"],
                "text": c["text"],
                "sentiment": c.get("sentiment")   # may be None
            })

        # Build response posts
        result = []
        for p in posts_data:
            result.append(Post(
                id=p["id"],
                caption=p["caption"],
                likes=p.get("likes_count", 0),
                comments=comments_by_post.get(p["id"], [])
            ))
        return result
    except Exception as e:
        print(f"Error fetching feed: {e}")
        return []

@router.post("/comment/{comment_id}/analyze", response_model=CommentAnalysis)
async def analyze_comment(comment_id: str):
    """Analyze a specific comment and generate a reply."""
    # First, fetch the comment from Supabase (or use the seeded data)
    # Since we don't have a direct endpoint to get a single comment, we'll query
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Fetch the comment
        comment_resp = supabase.table("instagram_comments").select("*").eq("id", comment_id).execute()
        if not comment_resp.data:
            raise HTTPException(status_code=404, detail="Comment not found")
        comment = comment_resp.data[0]

        # Fetch the post to get caption
        post_resp = supabase.table("instagram_posts").select("caption").eq("id", comment["post_id"]).execute()
        post_caption = post_resp.data[0]["caption"] if post_resp.data else ""

        analysis = analyze_comment_with_gemini(comment["text"], post_caption)

        # Update the comment with sentiment and ai_reply
        supabase.table("instagram_comments").update({
            "sentiment": analysis["sentiment"],
            "ai_reply": analysis["suggested_reply"]
        }).eq("id", comment_id).execute()

        return CommentAnalysis(**analysis)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in analyze_comment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/engagement", response_model=List[PostEngagement])
async def get_engagement():
    """Compute engagement scores for all posts from Supabase."""
    if not supabase:
        return []

    try:
        posts_resp = supabase.table("instagram_posts").select("*").execute()
        posts_data = posts_resp.data or []

        # Predefine product names (you could fetch from products table if exists)
        # For simplicity, we'll use a static list; but ideally you'd fetch from products DB.
        product_names = ["curry puff", "roti canai", "onde-onde", "spicy curry puff", "kaya puff"]

        results = []
        for p in posts_data:
            # Detect products mentioned in caption
            caption = p.get("caption", "").lower()
            mentioned = set()
            for name in product_names:
                if name in caption:
                    mentioned.add(name)

            score = p.get("likes_count", 0) * 1 + p.get("comments_count", 0) * 2
            results.append(PostEngagement(
                post_id=p["id"],
                total_likes=p.get("likes_count", 0),
                total_comments=p.get("comments_count", 0),
                top_products=list(mentioned),
                engagement_score=score
            ))
        return results
    except Exception as e:
        print(f"Error computing engagement: {e}")
        return []

@router.get("/engagement-over-time")
async def get_engagement_over_time(group_by: str = "day"):
    """
    Returns engagement (likes + comments) aggregated by day, week, month, quarter, or year.
    group_by: day, week, month, quarter, year
    """
    if not supabase:
        return []

    try:
        posts_resp = supabase.table("instagram_posts").select("id, likes_count, comments_count, fetched_at").execute()
        posts = posts_resp.data or []
        if not posts:
            return []

        # Group by the requested time period
        grouped = defaultdict(int)

        for post in posts:
            fetched = post.get("fetched_at")
            if not fetched:
                continue
            # Parse timestamp (assuming ISO format)
            try:
                dt = datetime.fromisoformat(fetched.replace('Z', '+00:00'))
            except:
                continue

            engagement = post.get("likes_count", 0) + post.get("comments_count", 0)

            if group_by == "day":
                key = dt.strftime("%Y-%m-%d")
            elif group_by == "week":
                # ISO week: year-week
                year, week, _ = dt.isocalendar()
                key = f"{year}-W{week:02d}"
            elif group_by == "month":
                key = dt.strftime("%Y-%m")
            elif group_by == "quarter":
                quarter = (dt.month - 1) // 3 + 1
                key = f"{dt.year}-Q{quarter}"
            elif group_by == "year":
                key = dt.strftime("%Y")
            else:
                key = dt.strftime("%Y-%m-%d")  # default day

            grouped[key] += engagement

        # Convert to list sorted by date
        result = [{"date": k, "engagement": v} for k, v in sorted(grouped.items())]
        return result
    except Exception as e:
        print(f"Error in engagement over time: {e}")
        return []