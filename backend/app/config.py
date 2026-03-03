"""
Configuration — loads environment variables from the root .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load the root-level .env (two directories up from backend/app/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# Clerk
CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY: str = os.getenv("VITE_CLERK_PUBLISHABLE_KEY", "")
CLERK_JWKS_URL: str = os.getenv("CLERK_JWKS_URL", "")

# Server
PORT: int = int(os.getenv("PORT", "8000"))
