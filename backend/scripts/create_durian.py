from app.supabase_client import supabase
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
res = supabase.table('products').insert(data).execute()
print(f"Result: {res.data}")
