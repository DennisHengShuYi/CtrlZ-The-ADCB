from app.supabase_client import supabase
import urllib.request
import json

print('BEFORE:')
print(supabase.table('products').select('inventory').eq('name', 'Durian Musang King').execute().data)

inv_res = supabase.table('invoices').select('id').eq('invoice_number', 'INV-20260312235434-00A7').execute()
inv_id = inv_res.data[0]['id']

data = json.dumps({"status": "paid"}).encode()
req = urllib.request.Request(
    f'http://127.0.0.1:8000/api/invoices/{inv_id}/status',
    data=data,
    headers={'Content-Type':'application/json', 'Authorization':'Bearer mock-token'},
    method='PATCH'
)

print('API RESULT:')
print(urllib.request.urlopen(req).read().decode())

print('AFTER:')
print(supabase.table('products').select('inventory').eq('name', 'Durian Musang King').execute().data)
