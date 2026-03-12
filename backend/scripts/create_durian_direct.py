import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUB_URL = os.getenv("SUPABASE_URL")
SUB_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

sb = create_client(SUB_URL, SUB_KEY)

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

res = sb.table('products').insert(data).execute()
print(res.data)
