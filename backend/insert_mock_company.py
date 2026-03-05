import sys
import os

sys.path.append(os.path.dirname(__file__))
from app.supabase_client import supabase

try:
    response = supabase.table("user_companies").insert({
        "user_id": "user_2test_mock_123456789",
        "name": "Mock Test Company",
        "address": "123 Mock Lane",
        "business_reg": "MOCK-123",
        "base_currency": "MYR"
    }).execute()
    print("Insertion successful:", response)
except Exception as e:
    print("Error:", e)
