import os, sys
from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()

supabase: Client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
res = supabase.table('invoices').select('invoice_number, date, total_amount, type, status').execute()
invoices = res.data

m_total = 0
other_total = 0
lines = []
for i in invoices:
    num = i.get('invoice_number') or '(none)'
    is_m = num.strip().upper().startswith('M') or num.strip().upper().startswith('INV')
    tag = "INCOME" if is_m else "EXPENSE"
    line = f"{tag} | {num} | {i['date']} | RM {i['total_amount']:,.2f} | {i.get('status','?')}"
    lines.append(line)
    if is_m:
        m_total += i['total_amount']
    else:
        other_total += i['total_amount']

print("ALL INVOICES FROM SUPABASE:")
for l in lines:
    print(l)
print(f"\nM/INV-prefix (Revenue):     RM {m_total:,.2f}")
print(f"Other invoices (Expense):     RM {other_total:,.2f}")
print(f"TOTAL ALL:                    RM {m_total+other_total:,.2f}")
print(f"\nWebsite shows: RM {m_total:,.2f} as Annual Revenue")
