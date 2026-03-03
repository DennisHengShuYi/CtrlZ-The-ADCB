"""
Supabase client — shared instance for all backend services.
"""

import os
from supabase import create_client, Client
from app.config import ROOT_DIR
from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("⚠️  SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — DB calls will fail.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
