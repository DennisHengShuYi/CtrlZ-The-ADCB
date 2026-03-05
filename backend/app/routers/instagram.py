import os
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from google import genai

# Load environment variables from the project root
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ Instagram: Gemini client initialized")
    except Exception as e:
        print(f"❌ Instagram: Failed to initialize Gemini client: {e}")
        client = None
else:
    print("⚠️ Instagram: No Gemini API key found, using fallback only")
    client = None

# Import shared Supabase client
from app.supabase_client import supabase

USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
if USE_SUPABASE:
    try:
        supabase.table("instagram_comments").select("*").limit(1).execute()
        print("✅ Instagram: Supabase connected")
    except Exception as e:
        print(f"❌ Instagram: Supabase connection failed: {e}")
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

# --- Simulated data (hardcoded for hackathon) ---
SAMPLE_POSTS = [
    Post(
        id="post1",
        caption="New curry puffs! Try our spicy variant 🔥",
        likes=120,
        comments=[
            Comment(id="c1", username="user1", text="Looks delicious!"),
            Comment(id="c2", username="user2", text="How much for 50 boxes?"),
            Comment(id="c3", username="user3", text="Expensive la 😕"),
        ]
    ),
    Post(
        id="post2",
        caption="Roti canai frozen – just heat and eat!",
        likes=85,
        comments=[
            Comment(id="c4", username="user4", text="Where to buy?"),
            Comment(id="c5", username="user5", text="Sedap! I want 10 packs"),
        ]
    )
]

# --- Initialize Instagram posts in Supabase (if empty) ---
def init_instagram_posts():
    if not USE_SUPABASE or not supabase:
        return
    try:
        existing = supabase.table("instagram_posts").select("id").limit(1).execute()
        if not existing.data:
            for post in SAMPLE_POSTS:
                supabase.table("instagram_posts").insert({
                    "id": post.id,
                    "caption": post.caption,
                    "likes_count": post.likes,
                    "comments_count": len(post.comments)
                }).execute()
            print("✅ Instagram: Sample posts stored in Supabase")
    except Exception as e:
        print(f"❌ Instagram: Failed to store sample posts: {e}")

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

# --- Helper: analyze comment with Gemini ---
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
    """Return simulated Instagram posts (from memory, not DB)."""
    return SAMPLE_POSTS

@router.post("/comment/{comment_id}/analyze", response_model=CommentAnalysis)
async def analyze_comment(comment_id: str):
    """Analyze a specific comment and generate a reply."""
    for post in SAMPLE_POSTS:
        for comment in post.comments:
            if comment.id == comment_id:
                analysis = analyze_comment_with_gemini(comment.text, post.caption)
                # Store in Supabase if enabled
                if USE_SUPABASE and supabase:
                    try:
                        supabase.table("instagram_comments").upsert({
                            "id": comment.id,
                            "post_id": post.id,
                            "username": comment.username,
                            "text": comment.text,
                            "sentiment": analysis["sentiment"],
                            "ai_reply": analysis["suggested_reply"]
                        }).execute()
                    except Exception as e:
                        print(f"Supabase insert failed: {e}")
                return CommentAnalysis(**analysis)
    raise HTTPException(status_code=404, detail="Comment not found")

@router.get("/engagement", response_model=List[PostEngagement])
async def get_engagement():
    """Compute engagement scores for all posts (from memory, not DB)."""
    results = []
    for post in SAMPLE_POSTS:
        product_mentions = set()
        if "curry puff" in post.caption.lower():
            product_mentions.add("curry puff")
        if "roti canai" in post.caption.lower():
            product_mentions.add("roti canai")
        score = post.likes * 1 + len(post.comments) * 2
        results.append(PostEngagement(
            post_id=post.id,
            total_likes=post.likes,
            total_comments=len(post.comments),
            top_products=list(product_mentions),
            engagement_score=score
        ))
    return results