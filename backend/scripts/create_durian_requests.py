import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SUB_URL = os.getenv("SUPABASE_URL")
SUB_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

url = f"{SUB_URL}/rest/v1/products"
headers = {
    "apikey": SUB_KEY,
    "Authorization": f"Bearer {SUB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

data = {
    'name': 'Durian Musang King',
    'inventory': 100,
    'threshold': 10,
    'company_id': 'f77f22a2-a57b-47bf-85d7-f1a17263d26c',
    'selling_price': 80.0,
    'unit': 'kg',
    'origin_country': 'MY',
    'details': {}
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
