import os
from pathlib import Path
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).resolve().parent.parent
print(f'Loading .env from: {ROOT_DIR / ".env"}')
load_dotenv(ROOT_DIR / '.env')
print(f'AUTH_STRATEGY: {os.getenv("AUTH_STRATEGY")}')