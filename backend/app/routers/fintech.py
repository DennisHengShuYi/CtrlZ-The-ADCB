from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os
import sqlite3
import numpy as np
from dotenv import load_dotenv
from google import genai as google_genai
from pathlib import Path
from supabase import create_client, Client

# Load .env from the project root (4 levels up: fintech.py → routers → app → backend → root)
_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)
print(f"[fintech.py] Loading .env from: {_ENV_PATH}")
print(f"[fintech.py] USE_SUPABASE env = {os.getenv('USE_SUPABASE')}")

USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Optional[Client] = None
if USE_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        USE_SUPABASE = False

router = APIRouter()

# Force no-cache on every response so browser always fetches fresh data from Supabase
# @router.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

DATABASE = "app/fintech.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # 1. High-level Revenue Metrics (Original analysis base)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS revenue_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            status TEXT,
            verified BOOLEAN,
            issued_date TEXT
        )
    ''')
    
    # 2. Functional Modules (Merged from "my component")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_info TEXT,
            business_reg TEXT,
            person_in_charge TEXT,
            type TEXT CHECK (type IN ('customer', 'supplier')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER REFERENCES clients(id),
            invoice_number TEXT NOT NULL,
            date TEXT NOT NULL,
            month TEXT NOT NULL,
            status TEXT DEFAULT 'unpaid',
            total_amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'MYR',
            exchange_rate REAL DEFAULT 1.0,
            type TEXT DEFAULT 'issuing',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER REFERENCES clients(id),
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            method TEXT,
            notes TEXT,
            currency TEXT DEFAULT 'MYR',
            exchange_rate REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            salary REAL,
            epf REAL,
            socso REAL,
            eis REAL,
            tax REAL,
            nric TEXT,
            dob TEXT,
            nationality TEXT,
            address TEXT,
            shares INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def seed_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if data already exists to avoid duplication
    cursor.execute("SELECT COUNT(*) FROM revenue_metrics")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Seed Revenue Metrics (Last 6 months)
    revenue_data = [
        (45000, 'paid', True, '2025-09-15'),
        (52000, 'paid', True, '2025-10-15'),
        (48000, 'paid', True, '2025-11-15'),
        (55000, 'paid', True, '2025-12-15'),
        (62000, 'paid', True, '2026-01-15'),
        (78000, 'unpaid', False, '2026-02-15'),
    ]
    cursor.executemany("INSERT INTO revenue_metrics (amount, status, verified, issued_date) VALUES (?, ?, ?, ?)", revenue_data)

    # 2. Seed Clients
    clients = [
        ('Global Tech Solutions', 'contact@globaltech.com', 'REG-12345', 'John Doe', 'customer'),
        ('Mega Corp', 'finance@megacorp.com', 'REG-67890', 'Jane Smith', 'customer'),
        ('Office Supplies Ltd', 'sales@officesupplies.my', 'REG-11223', 'Bob Marley', 'supplier'),
        ('Cloud Services Hub', 'billing@cloudhub.com', 'REG-44556', 'Alice Cooper', 'supplier'),
    ]
    cursor.executemany("INSERT INTO clients (name, contact_info, business_reg, person_in_charge, type) VALUES (?, ?, ?, ?, ?)", clients)
    
    # 3. Seed Invoices
    # Supplier Invoices (Expenses)
    cursor.execute("SELECT id FROM clients WHERE type = 'supplier'")
    supplier_ids = [r[0] for r in cursor.fetchall()]
    
    supplier_invoices = [
        (supplier_ids[0], 'INV-SUP-001', '2026-02-01', '2026-02', 'unpaid', 12000, 'MYR'),
        (supplier_ids[1], 'INV-SUP-002', '2026-02-10', '2026-02', 'unpaid', 8500, 'MYR'),
    ]
    cursor.executemany("INSERT INTO invoices (client_id, invoice_number, date, month, status, total_amount, currency) VALUES (?, ?, ?, ?, ?, ?, ?)", supplier_invoices)

    # Customer Invoices (Assets/Receivables)
    cursor.execute("SELECT id FROM clients WHERE type = 'customer'")
    customer_ids = [r[0] for r in cursor.fetchall()]

    customer_invoices = [
        (customer_ids[0], 'INV-CUST-001', '2026-01-20', '2026-01', 'paid', 45000, 'MYR'),
        (customer_ids[1], 'INV-CUST-002', '2026-02-15', '2026-02', 'unpaid', 35000, 'MYR'),
    ]
    cursor.executemany("INSERT INTO invoices (client_id, invoice_number, date, month, status, total_amount, currency) VALUES (?, ?, ?, ?, ?, ?, ?)", customer_invoices)

    # 4. Seed Payments (Cash Flow)
    payments = [
        (customer_ids[0], 45000, '2026-01-25', 'Bank Transfer', 'Payment for INV-CUST-001'),
        (supplier_ids[0], 5000, '2026-02-05', 'Online Banking', 'Partial payment for INV-SUP-001'),
    ]
    cursor.executemany("INSERT INTO payments (client_id, amount, date, method, notes) VALUES (?, ?, ?, ?, ?)", payments)

    # 5. Seed Staff (Malaysia Statutory Rates: EPF 13%, SOCSO 1.75%, EIS 0.2%)
    staff_data = [
        ('Alex Wong Kah Leong', 'Director', 15000, 1950, 262.5, 30, 1200, '850412-14-5678', '1985-04-12', 'Malaysian', 'No. 22, Jalan SS 2/55, Petaling Jaya, 47300 Selangor', 60),
        ('Siti Aminah binti Rashid', 'Director', 12000, 1560, 210, 24, 800, '880718-56-7890', '1988-07-18', 'Malaysian', 'No. 5, Jalan Bukit Bintang, 55100 Kuala Lumpur', 40),
        ('Raj Kumar', 'Engineer', 6000, 780, 105, 12, 300, '900515-10-1234', '1990-05-15', 'Malaysian', 'No. 10, Jalan Ampang, 50450 KL', 0),
    ]
    cursor.executemany("INSERT INTO staff (name, role, salary, epf, socso, eis, tax, nric, dob, nationality, address, shares) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", staff_data)

    conn.commit()
    conn.close()

if not USE_SUPABASE:
    init_db()
    seed_db()

# --- Models ---
class AnalysisResult(BaseModel):
    revenueConsistency: float
    cashFlowCoverage: float
    debtToIncome: float
    collectionEfficiency: float
    complianceScore: float
    totalRevenue: float
    annualRevenue: float
    loanReadinessScore: float
    totalExpenses: float
    netProfitMargin: float
    assetScore: float
    cashflowScore: float
    dtiScore: float
    totalAssets: float
    cashOnHand: float
    availableForExpenses: float
    staffCount: int
    monthlyTax: float
    invoiceCount: int
    outMoney: float
    currentEfficiency: float
    proposedLoanValue: float
    # Dynamic indicator fields
    currentMonthCustomerInvoices: int   # invoices TO customers THIS month
    prevMonthCustomerInvoices: int      # invoices TO customers LAST month (for % change)
    currentMonthRevenue: float          # revenue earned THIS month
    prevMonthRevenue: float             # revenue earned LAST month (for % change)
    prevLoanReadinessScore: float       # readiness score last month (for % change)
    loanApprovalProbability: float      # score from rules-based or CTOS

class ClientForm(BaseModel):
    name: str
    contact_info: Optional[str] = None
    business_reg: Optional[str] = None
    person_in_charge: Optional[str] = None
    type: str

class InvoiceForm(BaseModel):
    client_id: str
    invoice_number: str
    date: str
    month: str
    currency: str = "MYR"
    exchange_rate: float = 1.0
    total_amount: float

# --- Endpoints ---

async def get_active_company(email: Optional[str] = None):
    """
    Returns (company_id, company_name) based on user email.
    Falls back to the earliest company if no email provided or not found.
    """
    if not USE_SUPABASE or not supabase:
        return None, "Ctrl-Z SDN BHD"
    
    try:
        if email:
            res = supabase.table('user_companies').select("id, name").eq('email', email).execute()
            if res.data:
                return res.data[0]['id'], res.data[0]['name']
        
        # Fallback
        res = supabase.table('user_companies').select("id, name").order('created_at').limit(1).execute()
        if res.data:
            return res.data[0]['id'], res.data[0]['name']
    except Exception as e:
        print(f"Error in get_active_company: {e}")
    
    return None, "Ctrl-Z SDN BHD"

# --- Invoice type helpers ---
# NEW RULE (user confirmed 2026-03-06):
from dateutil.relativedelta import relativedelta

async def get_dynamic_divisor(invoices_list: list) -> int:
    """
    Calculates the divisor based on company start date (earliest client created_at)
    and the latest invoice date. Capped at 12 months.
    """
    try:
        if not USE_SUPABASE or not supabase:
            return 12

        # 1. Get company start date (Earliest created_at from user_companies)
        company_res = supabase.table('user_companies').select('created_at').order('created_at').limit(1).execute()
        if not company_res.data:
            return 12
        
        start_date_str = company_res.data[0]['created_at'].split("T")[0]
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
        # 2. Get latest invoice date or Today
        if invoices_list:
            latest_inv_str = max(i['date'] for i in invoices_list)
            # Handle possible full timestamps
            if "T" in latest_inv_str: latest_inv_str = latest_inv_str.split("T")[0]
            latest_date = datetime.datetime.strptime(latest_inv_str, "%Y-%m-%d").date()
        else:
            latest_date = datetime.date(2026, 3, 6) # Using metadata today
            
        rdelta = relativedelta(latest_date, start_date)
        months_diff = rdelta.years * 12 + rdelta.months + (1 if rdelta.days > 0 else 0)
        
        divisor = min(max(1, months_diff), 12)
        print(f"DEBUG DIVISOR: Start={start_date}, Latest={latest_date}, Diff={months_diff}mo, Result={divisor}")
        return divisor
    except Exception as e:
        print(f"Error calculating dynamic divisor: {e}")
        return 12

#   invoice_number starts with 'M' (or 'm') → customer invoice (income/issuing)
#   anything else                            → supplier invoice (expense/receiving)
# The stored 'type' column is used as a secondary fallback only.
def _inv_num(i):
    return (i.get('invoice_number') or '').strip()

def is_issuing_invoice(i):
    """Customer revenue invoice: strictly must start with 'M' or 'INV' (case-insensitive)."""
    inv_num = _inv_num(i).upper()
    return inv_num.startswith('M') or inv_num.startswith('INV')

def is_receiving_invoice(i):
    """Supplier expense invoice: anything that is NOT a customer invoice."""
    return not is_issuing_invoice(i)


@router.get("/api/analysis", response_model=AnalysisResult)
async def perform_analysis(proposed_loan: float = 25000, email: Optional[str] = None):
    # Initialize variables
    total_revenue = 0
    total_out_money = 0
    cash_on_hand = 0
    total_assets = 0
    available_for_expenses = 0
    consistency = 100
    collection_eff = 0
    compliance_score = 100
    invoice_count = 0
    monthly_avg_revenue = 0
    monthly_avg_supplier_expenses = 0
    # Compliance flags
    has_business_reg = False
    is_tax_submitted = False
    # Dynamic indicator defaults
    current_month_cust_inv = 0
    prev_month_cust_inv = 0
    current_month_rev = 0.0
    prev_month_rev = 0.0
    
    if USE_SUPABASE and supabase:
        try:
            # BROAD ACCESS: Fetch all invoices and payments regardless of email
            invoices_res = supabase.table('invoices').select('*, clients(*)').execute()
            payments_res = supabase.table('payments').select('*, clients(*)').execute()
            staff_res = supabase.table('staff').select('*').execute()
            
            invoices = invoices_res.data
            payments = payments_res.data
            raw_staff = staff_res.data
            
            # --- Trailing 12-Month (TTM) Filter Logic ---
            import datetime as dt
            from dateutil.relativedelta import relativedelta
            
            # Today's date based on metadata (2026-03-06)
            today = dt.date(2026, 3, 6)
            ttm_start_date = (today.replace(day=1) - relativedelta(months=11)).strftime("%Y-%m-%d")

            # --- Compliance Check (Business Reg & Tax) ---
            if email:
                comp_res = supabase.table('user_companies').select('*').eq('email', email).execute()
            else:
                comp_res = supabase.table('user_companies').select('*').order('created_at').limit(1).execute()
            
            company_data = comp_res.data[0] if comp_res.data else {}
            has_business_reg = bool(company_data.get('business_reg'))
            compliance_status_year = company_data.get('compliance_status')
            current_year = today.year
            is_tax_submitted = str(compliance_status_year) == str(current_year)
            
            # User Rule: 50% for Business Registration, 50% for Tax Form Submission
            compliance_score = (50 if has_business_reg else 0) + (50 if is_tax_submitted else 0)
            print(f"DEBUG COMPLIANCE: Reg={has_business_reg}, TaxSubmitted={is_tax_submitted} (Year {compliance_status_year}), Score={compliance_score}")
            
            # Filter invoices to ONLY include those within the last 12 months
            # Guard against None or missing date fields to prevent silent TypeError crash
            ttm_invoices = [i for i in invoices if i.get('date') and str(i['date'])[:10] >= ttm_start_date]
            print(f"DEBUG TTM: {len(invoices)} total invoices, {len(ttm_invoices)} in TTM window (>= {ttm_start_date})")
            
            # --- Issuing (TTM Revenue) ---
            # Rule: invoice starts with 'M' = customer income
            issuing_invoices = [i for i in ttm_invoices if is_issuing_invoice(i)]
            total_revenue = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in issuing_invoices)
            print(f"DEBUG ISSUING: {len(issuing_invoices)} customer invoices, revenue = {total_revenue}")
            
            # FORCE 12-MONTH DIVISOR FOR STANDARDIZATION (USER REQUEST 2026-03-12)
            divisor = 12
            monthly_avg_revenue = total_revenue / divisor
            print(f"DEBUG ANALYSIS: Total Rev={total_revenue}, Standard Divisor={divisor}, Monthly Avg Rev={monthly_avg_revenue}")
            
            # Metrics for Collection Efficiency (TTM only)
            paid_count = sum(1 for i in issuing_invoices if i['status'] == 'paid')
            collection_eff = (paid_count / len(issuing_invoices)) * 100 if issuing_invoices else 0

            # Revenue Consistency (TTM only)
            monthly_revs_map = {}
            for i in issuing_invoices:
                m = i['date'][:7]
                amount_myr = float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0)
                monthly_revs_map[m] = monthly_revs_map.get(m, 0) + amount_myr
            
            rev_list = list(monthly_revs_map.values())
            # Pad with zeros for months in the 12-month window with no revenue
            while len(rev_list) < 12:
                rev_list.append(0)
                
            if len(rev_list) > 1:
                cv = np.std(rev_list) / np.mean(rev_list) if np.mean(rev_list) > 0 else 0
                consistency = max(0, 100 - (cv * 50))
            else:
                consistency = 100

            # --- Receiving (TTM Expenses) ---
            # Rule: invoice_number not starting with 'M' = supplier expense
            receiving_invoices = [i for i in ttm_invoices if is_receiving_invoice(i)]
            total_supplier_expenses = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in receiving_invoices)
            monthly_avg_supplier_expenses = total_supplier_expenses / divisor
            print(f"DEBUG ANALYSIS: Total Supp (MYR-converted)={total_supplier_expenses}, Monthly Avg Supp={monthly_avg_supplier_expenses}")


            # --- Cash Flow (Based on Paid Invoices) ---
            # Rule: Use 'invoices' table instead of 'payments' as per user request
            cust_paid_invoices_sum = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in invoices if is_issuing_invoice(i) and i['status'] == 'paid')
            supp_paid_invoices_sum = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in invoices if is_receiving_invoice(i) and i['status'] == 'paid')

            # --- Payroll Calculation ---
            # Rule: Calculate total annual commitment to deduct from liquid cash
            temp_staff_list = []
            for s in raw_staff:
                salary = s.get('salary') or 0
                epf = (salary * s['epf_rate']) if s.get('epf_rate') is not None else (s.get('epf') or (salary * 0.13))
                socso = (salary * s['socso_rate']) if s.get('socso_rate') is not None else (s.get('socso') or (salary * 0.0175))
                eis = (salary * s['eis_rate']) if s.get('eis_rate') is not None else (s.get('eis') or (salary * 0.002))
                tax = (salary * s['tax_rate']) if s.get('tax_rate') is not None else (s.get('tax') or calculate_pcb(salary))
                temp_staff_list.append({"salary": salary, "epf": epf, "socso": socso, "eis": eis, "tax": tax})
            
            m_payroll = sum(s['salary'] for s in temp_staff_list)
            annual_payroll = m_payroll * 12

            # MODIFIED: User wants Cash On Hand to reflect deduction of ALL supplier invoices AND Staff Salary
            # for a more realistic net liquidity view (surplus cash).
            cash_on_hand = cust_paid_invoices_sum - total_supplier_expenses - annual_payroll
            total_out_money = total_supplier_expenses + annual_payroll

            # Assets (Liquidity Snapshot)
            # Refined: Cash + Discounted Receivables (80% value) - Pending Liabilities
            unpaid_cust_invoices_sum = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in issuing_invoices if i['status'] != 'paid')
            pending_supp_bills = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in receiving_invoices if i['status'] != 'paid')
            
            # Asset Strength Logic: 
            # 1. Start with Cash (Already net of all supplier invoices as per user request)
            # 2. Add 80% of what customers owe (discounted for collection risk)
            # Note: Deducting pending_supp_bills here would be double-deduction since they are in cash_on_hand
            total_assets = max(0.0, cash_on_hand + (unpaid_cust_invoices_sum * 0.8))
            invoice_count = len(issuing_invoices)
            available_for_expenses = cash_on_hand - pending_supp_bills
            
            # Count only invoices whose invoice_number contains 'inv' (case-insensitive)
            invoice_count = sum(1 for i in invoices if 'inv' in (i.get('invoice_number') or '').lower())

            # --- Dynamic Indicator Calculations ---
            # Momentum logic: Latest month vs Previous month in the dataset
            monthly_revs_sorted = sorted(monthly_revs_map.items()) 
            if monthly_revs_sorted:
                # Latest month data
                l_month, l_rev = monthly_revs_sorted[-1]
                current_month_rev = l_rev
                current_month_cust_inv = sum(1 for i in issuing_invoices if i['date'][:7] == l_month)
                
                if len(monthly_revs_sorted) > 1:
                    p_month, p_rev = monthly_revs_sorted[-2]
                    prev_month_rev = p_rev
                    prev_month_cust_inv = sum(1 for i in issuing_invoices if i['date'][:7] == p_month)
            
            
        except Exception as e:
            import traceback
            print(f"Supabase analysis error: {e}")
            print(traceback.format_exc())
            invoice_count = 0
            monthly_avg_revenue = 0
            monthly_avg_supplier_expenses = 0

    # --- Payroll & Net Income ---
    staff_list = []
    if USE_SUPABASE and supabase:
        try:
            # BROAD ACCESS for staff in analysis (as requested)
            staff_res = supabase.table('staff').select('*').execute()
            
            for s in staff_res.data:
                salary = s.get('salary') or 0
                # Fallback chain: rate column (multiplier) -> absolute column -> default calculation
                # epf_rate, socso_rate, etc are usually 0.13, 0.0175 etc in the database
                epf = (salary * s['epf_rate']) if s.get('epf_rate') is not None else (s.get('epf') or (salary * 0.13))
                socso = (salary * s['socso_rate']) if s.get('socso_rate') is not None else (s.get('socso') or (salary * 0.0175))
                eis = (salary * s['eis_rate']) if s.get('eis_rate') is not None else (s.get('eis') or (salary * 0.002))
                tax = (salary * s['tax_rate']) if s.get('tax_rate') is not None else (s.get('tax') or calculate_pcb(salary))
                staff_list.append({
                    "name": s.get('name', 'Unknown'),
                    "salary": salary, 
                    "epf": epf, 
                    "socso": socso, 
                    "eis": eis, 
                    "tax": tax
                })
        except Exception as e:
            print(f"Error fetching staff in analysis: {e}")
    
    if not staff_list:
        staff_list = []

    monthly_payroll_gross = sum(s['salary'] for s in staff_list)
    monthly_statutory_total = sum(s['epf'] + s['socso'] + s['eis'] + s.get('tax', 0) for s in staff_list)
    
    # RULE: User states RM 39k gross already includes all statutory costs
    # Net income = Average monthly's revenue (TTM) - Average monthly expenses (TTM)
    monthly_avg_expenses = monthly_avg_supplier_expenses + monthly_payroll_gross
    monthly_net_income = monthly_avg_revenue - monthly_avg_expenses
    print(f"DEBUG ANALYSIS: monthly_avg_revenue={monthly_avg_revenue}, Total Payroll={monthly_payroll_gross}, Supp Exp={monthly_avg_supplier_expenses}, Net={monthly_net_income}")
    
    # DTI (Debt 5000)
    dti_percentage = (5000 / max(1, monthly_net_income)) * 100 if monthly_net_income > 0 else 100
    
    # Loan Readiness
    cash_flow_cov = float(monthly_net_income) / float(proposed_loan) if monthly_net_income > 0 else 0.0
    asset_score = min(100.0, (float(total_assets) / 200000.0) * 100.0) if total_assets > 0 else 0.0
    dti_score = max(0.0, 100.0 - float(dti_percentage))
    cashflow_score = min(100.0, float(cash_flow_cov) * 100.0)
    
    weights = {'consistency': 0.15, 'collection': 0.10, 'compliance': 0.10, 'cashflow': 0.30, 'dti': 0.20, 'assets': 0.15}
    readiness = (consistency * weights['consistency'] + 
                 collection_eff * weights['collection'] + 
                 compliance_score * weights['compliance'] + 
                 cashflow_score * weights['cashflow'] + 
                 dti_score * weights['dti'] + 
                 asset_score * weights['assets'])
    
    # Simple probability ruleset based on final weighted score
    if readiness >= 80: bank_prob = 95
    elif readiness >= 65: bank_prob = 85
    elif readiness >= 50: bank_prob = 65
    else: bank_prob = 35
    
    current_eff_aggregated = (consistency + collection_eff) / 2

    # Tax (On annualized active profit)
    annual_profit_est = max(0, monthly_net_income * 12)
    if annual_profit_est <= 150000:
        annual_tax_est = annual_profit_est * 0.15
    elif annual_profit_est <= 600000:
        annual_tax_est = (150000 * 0.15) + (annual_profit_est - 150000) * 0.17
    else:
        annual_tax_est = (150000 * 0.15) + (450000 * 0.17) + (annual_profit_est - 600000) * 0.24
    monthly_tax = annual_tax_est / 12

    # --- Real 6-Month Positive Cash Flow Ratio (Silver/Gold Logic) ---
    ratio_debug_lines = []
    try:
        from app.currency_service import fetch_exchange_rate
        monthly_net_flow = {}
        ratio_debug_lines.append("--- INVOICE CURRENCY CONVERSION & CLASSIFICATION ---")
        ratio_debug_lines.append(f"(Note: Each month below will also be subtracted by total monthly payroll: RM {monthly_payroll_gross:,.2f})")
        for inv in invoices:
            inv_date = inv.get('date')
            if not inv_date: continue
            
            month = str(inv_date)[:7]
            amount = float(inv.get('total_amount') or 0)
            exchange_rate = float(inv.get('exchange_rate') or 1.0)
            inv_num = str(inv.get('invoice_number') or '')
            
            # Currency conversion logic
            amount_myr = amount * exchange_rate
                
            # Customer (M... or INV...) vs Supplier
            is_issuing = inv_num.upper().startswith('M') or inv_num.upper().startswith('INV')
            if is_issuing:
                monthly_net_flow[month] = monthly_net_flow.get(month, 0) + amount_myr
            else:
                monthly_net_flow[month] = monthly_net_flow.get(month, 0) - amount_myr
        
        # SUBTRACT MONTHLY SALARY FROM EACH MONTH
        for m in monthly_net_flow:
            monthly_net_flow[m] -= monthly_payroll_gross
                
        ratio_debug_lines.append("\n--- MONTHLY RATIO SNAPSHOT ---")
        months_sorted = sorted(list(monthly_net_flow.keys()), reverse=True)[:6]
        positive_count = 0
        for m in sorted(months_sorted):
            val = monthly_net_flow[m]
            status = "POSITIVE" if val > 0 else "NEGATIVE/NEUTRAL"
            if val > 0: positive_count += 1
            ratio_debug_lines.append(f"  {m}: RM {val:,.2f} | {status}")
            
        ratio_debug_lines.append("\n--- FINAL RATIO CALCULATION (SILVER TIER LOGIC) ---")
        ratio_val = (positive_count / len(months_sorted) * 100) if months_sorted else 0
        ratio_debug_lines.append(f"  Analyzed contiguous months: {months_sorted}")
        ratio_debug_lines.append(f"  Months strictly > 0: {positive_count} out of {len(months_sorted)}")
        ratio_debug_lines.append(f"  Final Positive Cash Flow Ratio: {ratio_val:.1f}%")
    except Exception as e:
        ratio_debug_lines.append(f"Error computing positive cash flow ratio: {e}")

    # --- GENERATE EXTREMELY DETAILED DEBUG LOG (USER REQUEST 2026-03-07) ---
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/calculation_debug.txt", "w", encoding="utf-8") as f:
            f.write(f"================================================================================\n")
            f.write(f"   DETAILED CALCULATION TRACE: {datetime.datetime.now()}\n")
            f.write(f"================================================================================\n\n")
            
            f.write("STEP 1: SUPABASE DATA RETRIEVAL\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"Requested table: 'invoices' | Total records found: {len(invoices)}\n")
            f.write(f"Requested table: 'payments' | Total records found: {len(payments)}\n")
            f.write(f"Requested table: 'staff'    | Total employees found: {len(staff_list)}\n")
            f.write(f"TTM Filtering range: Records on or after {ttm_start_date}\n")
            f.write(f"TTM Invoices filtered: {len(ttm_invoices)}\n\n")

            f.write("STEP 2: ANNUAL REVENUE & AVG MONTHLY INCOME (TRAILING 12 MONTHS)\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"Rule: Customer invoices identified by 'M' prefix in invoice number.\n")
            f.write(f"Number of Customer Invoices (TTM): {len(issuing_invoices)}\n")
            raw_rev_sum = total_revenue
            f.write(f"Calculated TTM Revenue Sum (MYR): RM {raw_rev_sum:,.2f}\n")
            f.write(f"Divisor (Monthly Period): {divisor} months (calculated from start date to latest invoice)\n")
            f.write(f"Average Monthly Income (Revenue): RM {monthly_avg_revenue:,.2f} (Formula: {raw_rev_sum:,.2f} / {divisor})\n")
            
            f.write(f"Annualized Revenue: RM {raw_rev_sum:,.2f}\n\n")

            f.write("STEP 3: PAYROLL CONTRIBUTION & MONTHLY EXPENSES\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"Individual Staff Breakdown (from Supabase 'staff' table):\n")
            for idx, s in enumerate(staff_list, 1):
                f.write(f"  {idx}. {s.get('name', 'Unknown')}:\n")
                f.write(f"     - Gross Salary: RM {s.get('salary', 0):,.2f}\n")
                f.write(f"     - EPF Contribution: RM {s.get('epf', 0):,.2f}\n")
                f.write(f"     - SOCSO Contribution: RM {s.get('socso', 0):,.2f}\n")
                f.write(f"     - EIS Contribution: RM {s.get('eis', 0):,.2f}\n")
                f.write(f"     - Monthly Tax (PCB): RM {s.get('tax', 0):,.2f}\n")
                net_pay_calc = s.get('salary',0) - s.get('epf',0) - s.get('socso',0) - s.get('eis',0) - s.get('tax',0)
                f.write(f"     - Resulting Net Pay: RM {net_pay_calc:,.2f}\n")
            
            f.write("\nSTEP 4: NET PROFIT & TAX CALCULATION (ARITHMETIC BREAKDOWN)\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"1. Monthly Revenue: RM {raw_rev_sum:,.2f} (Annual) / {divisor} = RM {monthly_avg_revenue:,.2f} /mo\n")
            f.write(f"2. Total Yearly Costs:\n")
            f.write(f"   Supplier Expenses (TTM): RM {total_supplier_expenses:,.2f}\n")
            f.write(f"   Payroll (Annualized): RM {monthly_payroll_gross * 12:,.2f} ({monthly_payroll_gross:,.2f} * 12)\n")
            yearly_costs = total_supplier_expenses + (monthly_payroll_gross * 12)
            f.write(f"   Total Costs: RM {yearly_costs:,.2f}\n")
            
            f.write(f"3. Monthly Net Profit:\n")
            f.write(f"   (RM {raw_rev_sum:,.2f} - RM {yearly_costs:,.2f}) / 12 = RM {monthly_net_income:,.2f}\n")
            
            f.write(f"4. Corporate Tax Calculation (Tiered):\n")
            f.write(f"   Annual Active Profit: RM {annual_profit_est:,.2f}\n")
            # Show tiers if profit > 0
            if annual_profit_est > 0:
                f.write(f"   - First 150k @ 15%: RM {min(annual_profit_est, 150000) * 0.15:,.2f}\n")
                if annual_profit_est > 150000:
                    f.write(f"   - Next 450k @ 17%: RM {min(max(0, annual_profit_est-150000), 450000) * 0.17:,.2f}\n")
                if annual_profit_est > 600000:
                    f.write(f"   - Above 600k @ 24%: RM {(annual_profit_est-600000) * 0.24:,.2f}\n")
            f.write(f"   Total Annual Tax: RM {annual_tax_est:,.2f}\n")
            f.write(f"   Monthly Tax Est: RM {monthly_tax:,.2f} (RM {annual_tax_est:,.2f} / 12)\n\n")

            f.write("STEP 5: READINESS FACTORS (DETAILED STEP-BY-STEP ARITHMETIC)\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"The Loan Score is calculated using weighted scores of 6 key factors:\n\n")
            
            f.write(f"1. Revenue Consistency (Weight: 15%)\n")
            f.write(f"   - Based on Coefficient of Variation (CV) of {len(rev_list)} monthly periods.\n")
            f.write(f"   - Raw Consistency Value: {consistency:.2f}%\n")
            f.write(f"   - Contribution to Total Score: {consistency * 0.15:.2f}pts\n\n")

            f.write(f"2. Collection Efficiency (Weight: 10%)\n")
            f.write(f"   - Formula: ({paid_count} Paid Invoices / {len(issuing_invoices) or 1} Total Invoices) * 100\n")
            f.write(f"   - Efficiency Value: {collection_eff:.2f}%\n")
            f.write(f"   - Contribution to Total Score: {collection_eff * 0.10:.2f}pts\n\n")

            f.write(f"3. Cash Flow Coverage (Weight: 30%)\n")
            f.write(f"   - Benchmarked against Proposed Monthly Repayment: RM {proposed_loan:,.2f}\n")
            f.write(f"   - Ratio: RM {monthly_net_income:,.2f} (Net) / RM {proposed_loan:,.2f} (Loan)\n")
            f.write(f"   - Coverage Score (Capped 100%): {cashflow_score:.2f}%\n")
            f.write(f"   - Contribution to Total Score: {cashflow_score * 0.30:.2f}pts\n\n")

            f.write(f"4. Debt-to-Income / DTI Score (Weight: 20%)\n")
            f.write(f"   - Existing Monthly Debt Load: RM 5,000.00\n")
            f.write(f"   - DTI Percentage: (5,000 / {max(1, monthly_net_income):,.2f}) * 100 = {dti_percentage:.2f}%\n")
            f.write(f"   - Resulting DTI Score (100 - DTI): {dti_score:.2f}%\n")
            f.write(f"   - Contribution to Total Score: {dti_score * 0.20:.2f}pts\n\n")

            f.write(f"5. Asset Strength (Weight: 15%)\n")
            f.write(f"   - Liquidity Calculation:\n")
            f.write(f"     Paid Customer Invoices: RM {cust_paid_invoices_sum:,.2f}\n")
            f.write(f"     - Total Supplier Expenses (MYR-conv): RM {total_supplier_expenses:,.2f}\n")
            f.write(f"     - Staff Salaries (Annualized): RM {annual_payroll:,.2f}\n")
            f.write(f"     = Adjusted Cash On Hand: RM {cash_on_hand:,.2f}\n")
            f.write(f"     + 80% Unpaid Receivables: RM {unpaid_cust_invoices_sum:,.2f} * 0.8 = RM {unpaid_cust_invoices_sum*0.8:,.2f}\n")
            f.write(f"   - Total Net Assets (Liquidity Snapshot): RM {total_assets:,.2f}\n")
            f.write(f"   - Asset Score (Relative to RM 200k target): {asset_score:.2f}%\n")
            f.write(f"   - Contribution to Total Score: {asset_score * 0.15:.2f}pts\n\n")

            f.write(f"6. Compliance Health (Weight: 10%)\n")
            f.write(f"   - Business Registration (SSM): {'DONE' if has_business_reg else 'PENDING'} (+50pts)\n")
            f.write(f"   - Tax Form Submission ({current_year}): {'DONE' if is_tax_submitted else 'PENDING'} (+50pts)\n")
            f.write(f"   - Final Compliance Score: {compliance_score:.2f}%\n")
            f.write(f"   - Contribution to Total Score: {compliance_score * 0.10:.2f}pts\n\n")

            f.write("STEP 6: REAL 6-MONTH POSITIVE CASH FLOW RATIO (FOR SILVER LOGIC)\n")
            f.write(f"--------------------------------------------------------------------------------\n")
            for line in ratio_debug_lines:
                f.write(f"{line}\n")
            f.write("\n")

            f.write(f"--------------------------------------------------------------------------------\n")
            f.write(f"FINAL WEIGHTED READINESS SCORE: {readiness:.2f}%\n")
            f.write(f"================================================================================\n")

    except Exception as log_err:
        import traceback
        print(f"Error writing trace log: {log_err}\n{traceback.format_exc()}")

    return AnalysisResult(
        revenueConsistency=float(round(float(consistency), 2)),
        cashFlowCoverage=float(round(float(cash_flow_cov), 2)),
        debtToIncome=float(round(float(dti_percentage), 2)),
        collectionEfficiency=float(round(float(collection_eff), 2)),
        complianceScore=float(round(float(compliance_score), 2)),
        totalRevenue=float(round(float(total_revenue), 2)),
        annualRevenue=float(round(float(monthly_avg_revenue * 12), 2)),
        totalExpenses=float(round(float(monthly_avg_expenses * 12), 2)),
        netProfitMargin=float(round((float(monthly_net_income) / float(current_month_rev) * 100.0) if current_month_rev > 0 else 0.0, 2)),
        loanReadinessScore=float(round(float(readiness), 2)),
        assetScore=float(round(float(asset_score), 2)),
        cashflowScore=float(round(float(cashflow_score), 2)),
        dtiScore=float(round(float(dti_score), 2)),
        totalAssets=float(round(float(total_assets), 2)),
        cashOnHand=float(round(float(cash_on_hand), 2)),
        availableForExpenses=float(round(float(available_for_expenses), 2)),
        staffCount=int(len(staff_list)),
        monthlyTax=float(round(float(monthly_tax), 2)),
        invoiceCount=int(invoice_count),
        outMoney=float(round(float(total_out_money), 2)),
        currentEfficiency=float(round(float(current_eff_aggregated), 2)),
        proposedLoanValue=float(proposed_loan),
        currentMonthCustomerInvoices=int(current_month_cust_inv),
        prevMonthCustomerInvoices=int(prev_month_cust_inv),
        currentMonthRevenue=float(round(float(current_month_rev), 2)),
        prevMonthRevenue=float(round(float(prev_month_rev), 2)),
        prevLoanReadinessScore=float(round(float(readiness), 2)),
        loanApprovalProbability=float(round(float(bank_prob), 2))
    )


@router.get("/api/revenue")
async def get_revenue(email: Optional[str] = None):
    if USE_SUPABASE and supabase:
        try:
            # BROAD ACCESS
            res = supabase.table('invoices').select('invoice_number, date, total_amount, exchange_rate, type').execute()
            data = res.data
            monthly = {}
            for r in data:
                # Rule: Only include invoices starting with 'M' or 'INV' (Customer Invoices)
                inv_num = (r.get('invoice_number') or '').strip().upper()
                if not (inv_num.startswith('M') or inv_num.startswith('INV')):
                    continue
                # Derive YYYY-MM from the date field (no separate 'month' column exists)
                m = r['date'][:7]
                
                # Apply exchange rate to ensure revenue is reflected in base currency (MYR)
                amount_base = float(r.get('total_amount') or 0) * float(r.get('exchange_rate') or 1.0)
                monthly[m] = monthly.get(m, 0) + amount_base
            return [{"month": m, "revenue": v} for m, v in sorted(monthly.items())]
        except Exception as e:
            print(f"Revenue fetch error: {e}")
            return []
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT SUBSTR(issued_date, 1, 7) as m, SUM(amount) FROM revenue_metrics GROUP BY m")
        rows = cursor.fetchall()
        conn.close()
        return [{"month": r[0], "revenue": r[1]} for r in rows]

# --- Company Info Endpoint ---

@router.get("/api/company")
async def get_company(email: Optional[str] = None):
    if not USE_SUPABASE or not supabase:
        return {"id": "default", "name": "Ctrl-Z SDN BHD", "business_reg": None, "compliance_status": 0}
    
    current_year = datetime.datetime.now().year
    
    try:
        if email:
            res = supabase.table('user_companies').select("id, name, business_reg, compliance_status").eq('email', email).execute()
            if res.data:
                comp_status_val = res.data[0].get('compliance_status')
                mapped_status = 1 if comp_status_val == current_year else 0
                return {
                    "id": res.data[0]['id'], 
                    "name": res.data[0]['name'], 
                    "business_reg": res.data[0].get('business_reg'),
                    "compliance_status": mapped_status
                }
        
        res = supabase.table('user_companies').select("id, name, business_reg, compliance_status").order('created_at').limit(1).execute()
        if res.data:
            comp_status_val = res.data[0].get('compliance_status')
            mapped_status = 1 if comp_status_val == current_year else 0
            return {
                "id": res.data[0]['id'], 
                "name": res.data[0]['name'], 
                "business_reg": res.data[0].get('business_reg'),
                "compliance_status": mapped_status
            }
    except Exception as e:
        print(f"Error fetching company details: {e}")

    active_comp_id, name = await get_active_company(email)
    return {"id": active_comp_id or "default", "name": name, "business_reg": None, "compliance_status": 0}

@router.post("/api/compliance/submit")
async def submit_compliance(request: Request):
    """Explicit endpoint to record compliance filings, marking the user's compliance_status with the current year."""
    if not USE_SUPABASE or not supabase:
        return {"success": True}
        
    try:
        data = await request.json()
        email = data.get('email')
        
        if not email:
            return {"error": "Email is required"}
            
        current_year = datetime.datetime.now().year
        
        # Verify they have SSM before allowing compliance status
        res = supabase.table('user_companies').select('business_reg').eq('email', email).execute()
        if res.data and res.data[0].get('business_reg'):
            supabase.table('user_companies').update({'compliance_status': current_year}).eq('email', email).execute()
            return {"success": True, "compliance_status": 1}
        else:
            return {"error": "Business Registration required first", "compliance_status": 0}
            
    except Exception as e:
        print(f"Error submitting compliance: {e}")
        return {"error": str(e)}

# --- Functional Module Endpoints (Merged) ---

@router.get("/api/clients/")
async def list_clients():
    if USE_SUPABASE and supabase:
        res = supabase.table('clients').select("*").execute()
        return {"clients": res.data}
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients")
        rows = cursor.fetchall()
        conn.close()
        return {"clients": [dict(r) for r in rows]}

@router.post("/api/clients/")
async def create_client(form: ClientForm):
    if USE_SUPABASE and supabase:
        supabase.table('clients').insert({
            "name": form.name,
            "contact_info": form.contact_info,
            "business_reg": form.business_reg,
            "person_in_charge": form.person_in_charge,
            "type": form.type
        }).execute()
        return {"status": "success"}
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clients (name, contact_info, business_reg, person_in_charge, type) VALUES (?, ?, ?, ?, ?)",
            (form.name, form.contact_info, form.business_reg, form.person_in_charge, form.type)
        )
        conn.commit()
        conn.close()
        return {"status": "success"}

@router.get("/api/invoices/")
async def list_invoices():
    if USE_SUPABASE and supabase:
        res = supabase.table('invoices').select("*, clients(name)").execute()
        # Flatten clients(name)
        data = []
        for r in res.data:
            r['client_name'] = r['clients']['name'] if r.get('clients') else "Unknown"
            data.append(r)
        return {"invoices": data}
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name as client_name 
            FROM invoices i 
            JOIN clients c ON i.client_id = c.id
        """)
        rows = cursor.fetchall()
        conn.close()
        return {"invoices": [dict(r) for r in rows]}

@router.post("/api/invoices/")
async def create_invoice(form: InvoiceForm):
    if USE_SUPABASE and supabase:
        supabase.table('invoices').insert({
            "client_id": form.client_id,
            "invoice_number": form.invoice_number,
            "date": form.date,
            "month": form.month,
            "currency": form.currency,
            "exchange_rate": form.exchange_rate,
            "total_amount": form.total_amount
        }).execute()
        return {"status": "success"}
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invoices (client_id, invoice_number, date, month, currency, exchange_rate, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (form.client_id, form.invoice_number, form.date, form.month, form.currency, form.exchange_rate, form.total_amount)
        )
        conn.commit()
        conn.close()
        return {"status": "success"}

@router.get("/api/currency/rate")
async def get_rate(from_curr: str, to: str):
    # Mocking real-time conversion
    base_rates = {"USD": 4.7, "EUR": 5.1, "SGD": 3.5, "MYR": 1.0}
    if from_curr in base_rates and to in base_rates:
        rate = base_rates[from_curr] / base_rates[to]
        return {"rate": rate}
    return {"rate": 1.0}

# --- Original Compliance & AI Endpoints ---

def calculate_pcb(monthly_salary):
    """Simplified Malaysia PCB (Monthly Tax Deduction) calculation for Demo"""
    annual_salary = monthly_salary * 12
    # Personal relief + EPF relief (simplified)
    taxable_income = max(0, annual_salary - 13000) 
    
    tax = 0
    if taxable_income <= 5000:
        tax = 0
    elif taxable_income <= 20000:
        tax = (taxable_income - 5000) * 0.01
    elif taxable_income <= 35000:
        tax = 150 + (taxable_income - 20000) * 0.03
    elif taxable_income <= 50000:
        tax = 600 + (taxable_income - 35000) * 0.06
    elif taxable_income <= 70000:
        tax = 1500 + (taxable_income - 50000) * 0.11
    elif taxable_income <= 100000:
        tax = 3700 + (taxable_income - 70000) * 0.19
    elif taxable_income <= 400000:
        tax = 9400 + (taxable_income - 100000) * 0.25
    elif taxable_income <= 600000:
        tax = 84400 + (taxable_income - 400000) * 0.26
    else:
        tax = 136400 + (taxable_income - 600000) * 0.28
        
    return round(tax / 12, 2)

@router.get("/api/compliance")
async def get_compliance(email: Optional[str] = None):
    staff_list = []
    total_rev_ttm = 0
    supp_exp_ttm = 0
    all_invoices: list = []
    
    if USE_SUPABASE and supabase:
        try:
            active_comp_id, business_name = await get_active_company(email)
            
            # Trailing 12-Month (TTM) Filter Logic
            import datetime as dt
            from dateutil.relativedelta import relativedelta
            today = dt.date(2026, 3, 6)
            ttm_start_date = (today.replace(day=1) - relativedelta(months=11)).strftime("%Y-%m-%d")
            
            # BROAD ACCESS for invoices
            invoices_res = supabase.table('invoices').select('invoice_number, total_amount, date, type, clients(*)').execute()
            
            # SPECIFIC ACCESS for staff (as requested for Compliance tab)
            if active_comp_id:
                staff_res = supabase.table('staff').select('*').eq('company_id', active_comp_id).execute()
            else:
                staff_res = supabase.table('staff').select('*').execute()
            
            all_invoices = invoices_res.data
            staff_list = staff_res.data
            
            ttm_invoices = [i for i in all_invoices if i.get('date') and str(i['date'])[:10] >= ttm_start_date]
            
            issuing = [i for i in ttm_invoices if is_issuing_invoice(i)]
            total_rev_ttm = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in issuing)
            
            supp_exp_ttm = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in ttm_invoices if is_receiving_invoice(i))
            
        except Exception as e:
            print(f"Supabase compliance fetch error: {e}")

    if not staff_list:
        staff_list = []

    payroll = []
    for s in staff_list:
        salary = s.get('salary') or 0
        epf = (salary * s['epf_rate']) if s.get('epf_rate') is not None else (s.get('epf', salary * 0.13))
        socso = (salary * s['socso_rate']) if s.get('socso_rate') is not None else (s.get('socso', salary * 0.0175))
        eis = (salary * s['eis_rate']) if s.get('eis_rate') is not None else (s.get('eis', salary * 0.002))
        tax = (salary * s['tax_rate']) if s.get('tax_rate') is not None else (s.get('tax', calculate_pcb(salary)))
        
        payroll.append({
            "id": str(s.get('id', '')),
            "name": s.get('name', 'Unknown'),
            "gross_salary": salary,
            "salary": salary, 
            "epf": round(epf, 2),
            "socso": round(socso, 2),
            "eis": round(eis, 2),
            "tax": round(tax, 2),
            "net_salary": round(salary - epf - socso - eis - tax, 2),
            "net": round(salary - epf - socso - eis - tax, 2)
        })
    
    # FORCE 12-MONTH DIVISOR FOR STANDARDIZATION (USER REQUEST 2026-03-12)
    active_months = 12
    monthly_staff_total = sum(p['gross_salary'] for p in payroll)
    monthly_avg_supp_exp = supp_exp_ttm / active_months
    monthly_avg_rev = total_rev_ttm / active_months
    
    estimated_monthly_profit = max(0, monthly_avg_rev - monthly_staff_total - monthly_avg_supp_exp)
    annual_profit = estimated_monthly_profit * 12
    
    if annual_profit <= 150000:
        annual_tax = annual_profit * 0.15
    elif annual_profit <= 600000:
        annual_tax = (150000 * 0.15) + (annual_profit - 150000) * 0.17
    else:
        annual_tax = (150000 * 0.15) + (450000 * 0.17) + (annual_profit - 600000) * 0.24
    
    monthly_tax = annual_tax / 12
    
    return {
        "monthly_tax": round(monthly_tax, 2),
        "total_revenue": total_rev_ttm,
        "payroll": payroll,
        "threshold_reached": total_rev_ttm >= 500000,
        "staff_count": len(payroll),
        "total_monthly_payroll": round(monthly_staff_total, 2),
        "metrics": {
            "active_months": active_months,
            "monthly_avg_rev": round(monthly_avg_rev, 2),
            "monthly_avg_supp_exp": round(monthly_avg_supp_exp, 2),
            "estimated_annual_profit": round(annual_profit, 2)
        }
    }

@router.get("/api/staff")
async def list_staff():
    if USE_SUPABASE and supabase:
        res = supabase.table('staff').select("*").execute()
        return {"staff": res.data}
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM staff")
        rows = cursor.fetchall()
        conn.close()
        return {"staff": [dict(r) for r in rows]}

@router.get("/api/staff/directors")
async def list_directors(email: Optional[str] = None):
    if USE_SUPABASE and supabase:
        active_comp_id, _ = await get_active_company(email)
        query = supabase.table('staff').select("*").eq('role', 'Director')
        if active_comp_id:
            query = query.eq('company_id', active_comp_id)
        res = query.execute()
        return {"directors": res.data}
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM staff WHERE role = 'Director'")
        rows = cursor.fetchall()
        conn.close()
        return {"directors": [dict(r) for r in rows]}

@router.post("/api/ssm/register")
async def ssm_register(data: dict):
    import random
    import string
    ref_no = "SSM-2026-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    digital_cert = "CERT-MY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return {
        "status": "success",
        "ref_no": ref_no,
        "digital_cert": digital_cert,
        "company_name": data.get("companyName", ""),
        "submitted_at": "2026-03-05",
        "message": "Your SSM application has been received and is under review. Processing time: 1-3 business days."
    }

@router.get("/api/ctos")
async def get_ctos(email: Optional[str] = None):
    import random, json as _json

    # --- 1. Calculate CTOS score dynamically ---
    # Factors (Malaysian Scoring Logic approx):
    # Payment History (35%), Amount Owed (30%), Length of History (15%), Credit Mix (10%), New Credit (10%)
    
    # 1a. Generate raw factors
    has_delayed_payment = random.choices([False, True], weights=[0.7, 0.3])[0]
    utilization_pct = random.randint(10, 95)
    history_months = random.randint(3, 180) # 3 months to 15 years
    has_short_history = history_months < 24
    inquiry_count = random.randint(0, 12)
    has_too_many_inquiries = inquiry_count > 3
    has_poor_mix = random.choices([True, False], weights=[0.4, 0.6])[0]
    has_legal_issue = random.choices([False, True], weights=[0.95, 0.05])[0]

    # --- 1b. Scoring Engine (Base: 300, Max: 850)
    current_score = 300
    
    calc_steps = [f"Base Score: {current_score}"]
    
    # Payment History (Max +192.5)
    if not has_delayed_payment: 
        current_score += 192.5
        calc_steps.append("Payment History: Perfect (+192.5)")
    else: 
        current_score += 30
        calc_steps.append("Payment History: Arrears detected (+30.0)")
    
    # Utilization (Max +165)
    if utilization_pct < 20: 
        current_score += 165
        calc_steps.append(f"Utilization ({utilization_pct}%): Excellent (+165.0)")
    elif utilization_pct < 40: 
        current_score += 130
        calc_steps.append(f"Utilization ({utilization_pct}%): Good (+130.0)")
    elif utilization_pct < 60: 
        current_score += 80
        calc_steps.append(f"Utilization ({utilization_pct}%): Fair (+80.0)")
    elif utilization_pct < 80: 
        current_score += 30
        calc_steps.append(f"Utilization ({utilization_pct}%): Poor (+30.0)")
    else: 
        current_score += 5
        calc_steps.append(f"Utilization ({utilization_pct}%): Very Poor (+5.0)")
    
    # History Length (Max +82.5)
    if history_months > 84: 
        current_score += 82.5
        calc_steps.append(f"History Length ({history_months}m): Deep (+82.5)")
    elif history_months > 48: 
        current_score += 65
        calc_steps.append(f"History Length ({history_months}m): Mature (+65.0)")
    elif history_months > 24: 
        current_score += 40
        calc_steps.append(f"History Length ({history_months}m): Average (+40.0)")
    else: 
        current_score += 10
        calc_steps.append(f"History Length ({history_months}m): Thin (+10.0)")
    
    # New Credit/Inquiries (Max +55)
    if inquiry_count <= 1: 
        current_score += 55
        calc_steps.append(f"Inquiries ({inquiry_count}): Minimal (+55.0)")
    elif inquiry_count <= 3: 
        current_score += 35
        calc_steps.append(f"Inquiries ({inquiry_count}): Moderate (+35.0)")
    elif inquiry_count <= 6: 
        current_score += 15
        calc_steps.append(f"Inquiries ({inquiry_count}): High (+15.0)")
    else: 
        current_score += 0
        calc_steps.append(f"Inquiries ({inquiry_count}): Excessive (+0.0)")
    
    # Credit Mix (Max +55)
    if not has_poor_mix: 
        current_score += 55
        calc_steps.append("Credit Mix: Balanced (+55.0)")
    else: 
        current_score += 20
        calc_steps.append("Credit Mix: Unbalanced (+20.0)")

    # Legal Records Penalty
    if has_legal_issue:
        current_score = max(300, current_score - 200)
        calc_steps.append("Legal Records: Active Litigation Penalty (-200.0)")

    score = round(float(current_score))
    calc_steps.append(f"Final Calculated Score: {score}")

    # --- 1b. Business Profile Variables ---
    active_comp_id, business_name = await get_active_company(email)
    
    if USE_SUPABASE and supabase:
        invoices_res = supabase.table('invoices').select('total_amount, date, type, invoice_number, status').execute()
        payments_res = supabase.table('payments').select('amount, client_id, clients(type)').execute()
        invoices = invoices_res.data
        payments = payments_res.data
        issuing_invoices = [i for i in invoices if is_issuing_invoice(i)]
        total_revenue = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in issuing_invoices)
        # FORCE 12-MONTH DIVISOR FOR STANDARDIZATION (USER REQUEST 2026-03-12)
        month_count = 12
        monthly_revenue = round(total_revenue / month_count)
        cust_payments = sum(float(p['amount']) * float(p.get('exchange_rate') or 1.0) for p in payments if (p.get('clients') and p['clients'].get('type') == 'customer'))
        supp_payments = sum(float(p['amount']) * float(p.get('exchange_rate') or 1.0) for p in payments if (p.get('clients') and p['clients'].get('type') == 'supplier'))
        cash_on_hand = round(cust_payments - supp_payments)
        unpaid_cust_invoices = sum(float(i.get('total_amount') or 0) * float(i.get('exchange_rate') or 1.0) for i in issuing_invoices if i['status'] != 'paid')
        total_assets = round(cash_on_hand + unpaid_cust_invoices)
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM revenue_metrics")
        total_revenue = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(DISTINCT SUBSTR(issued_date,1,7)) FROM revenue_metrics")
        month_count = cursor.fetchone()[0] or 1
        monthly_revenue = round(total_revenue / month_count)
        cursor.execute("SELECT SUM(p.amount) FROM payments p JOIN clients c ON p.client_id = c.id WHERE c.type = 'customer'")
        customer_payments = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(p.amount) FROM payments p JOIN clients c ON p.client_id = c.id WHERE c.type = 'supplier'")
        supplier_payments = cursor.fetchone()[0] or 0
        cash_on_hand = round(customer_payments - supplier_payments)
        unpaid_cust_invoices = 0
        total_assets = cash_on_hand
        conn.close()

    target_loan = random.choice([50000, 100000, 150000, 200000, 250000, 500000])

    # --- 2. Dynamic Decision & Probability ---
    # Probability is anchored by Grade but varies linearly with Score within the category
    prob_calc = []
    
    if score >= 744:
        grade, decision = "Excellent", "Approved - Premium Rates"
        # 80% to 95% base
        base_prob = 80 + round((score - 744) / (850 - 744) * 15)
        prob_calc.append(f"Grade: {grade} (Score-Weighted Base: {base_prob}%)")
    elif score >= 697:
        grade, decision = "Good", "Approved - Standard Rates"
        # 60% to 79% base
        base_prob = 60 + round((score - 697) / (743 - 697) * 19)
        prob_calc.append(f"Grade: {grade} (Score-Weighted Base: {base_prob}%)")
    elif score >= 651:
        grade, decision = "Fair", "Approved with Conditions (Collateral Req)"
        # 30% to 59% base
        base_prob = 30 + round((score - 651) / (696 - 651) * 29)
        prob_calc.append(f"Grade: {grade} (Score-Weighted Base: {base_prob}%)")
    else:
        grade, decision = "Low", "Rejected - High Risk Profile"
        # 5% to 29% base
        base_prob = 5 + round((score - 300) / (650 - 300) * 24)
        prob_calc.append(f"Grade: {grade} (Score-Weighted Base: {base_prob}%)")

    # DSR adjustment (-25% to +10%)
    repayment_est = target_loan / 60
    dsr_factor = (monthly_revenue * 0.4) / max(1, repayment_est)
    prob_calc.append(f"DSR Calculation: (RM {monthly_revenue} rev * 0.4) / RM {round(repayment_est)} repayment = {round(dsr_factor, 2)}")
    
    if dsr_factor > 1.2: 
        dsr_adj = 10
        prob_calc.append("DSR Bonus: Strong (+10%)")
    elif dsr_factor > 0.8: 
        dsr_adj = 0
        prob_calc.append("DSR Adjustment: Neutral (+0%)")
    elif dsr_factor > 0.5: 
        dsr_adj = -10
        prob_calc.append("DSR Penalty: Weak (-10%)")
    else: 
        dsr_adj = -25
        prob_calc.append("DSR Penalty: Critical (-25%)")

    random_variance = random.randint(-5, 5)
    prob = min(98, max(2, base_prob + dsr_adj + random_variance))
    prob_calc.append(f"Random Variance: {random_variance}%")
    prob_calc.append(f"Final Probability: {prob}%")

    # Log calculations to debug file
    log_dir = Path(__file__).parent.parent.parent / "logs"
    os.makedirs(log_dir, exist_ok=True)
    with open(log_dir / "calculation_debug.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- {datetime.datetime.now()} ---\n")
        f.write("CTOS SCORE BREAKDOWN:\n")
        for step in calc_steps:
            f.write(f"  - {step}\n")
        f.write("\nLOAN PROBABILITY ENGINE:\n")
        for p_step in prob_calc:
            f.write(f"  - {p_step}\n")
        f.write(f"Parameters: Enrollment=True, Business={business_name}, TargetLoan=RM {target_loan:,}\n")

    # --- 3. Elements ---
    elements = []
    elements.append({"name": "Payment History", "value": "Warning" if has_delayed_payment else "Excellent",
                     "explanation": "We detected recent delayed payments. This is actively suppressing your score." if has_delayed_payment
                     else "Perfect repayment record. This is a massive positive signal for partner banks."})
    
    elements.append({"name": "Credit Utilization", "value": f"{utilization_pct}%",
                     "explanation": "High utilization detected (over 60%). Banks see this as a sign of cash flow stress." if utilization_pct > 60
                     else "Healthy utilization. You are using credit responsibly without overleveraging."})

    history_label = f"{round(history_months/12, 1)} Years" if history_months >= 12 else f"{history_months} Months"
    elements.append({"name": "Credit History Length", "value": history_label,
                     "explanation": "Limited track record. Lenders prefer at least 24 months of established history." if has_short_history
                     else f"Solid {history_label} history establishes you as a reliable long-term borrower."})

    elements.append({"name": "Credit Mix", "value": "Poor" if has_poor_mix else "Average",
                     "explanation": "Lack of diversified credit facilities (mostly unsecured/cards) is a risk factor." if has_poor_mix
                     else "Balanced mix of secured and unsecured facilities demonstrates mature debt management."})

    elements.append({"name": "Recent Inquiries", "value": str(inquiry_count),
                     "explanation": f"High inquiry count ({inquiry_count}). Too many hard checks in 90 days reduce your score." if inquiry_count > 3
                     else "Optimal inquiry level. Your profile shows stable credit seeking behavior."})


    # --- 4. Identify Active Issues ---
    issues = []
    if utilization_pct > 60: # Match the explanation logic
        issues.append(f"High credit utilization at {utilization_pct}%")
    if has_delayed_payment:
        issues.append("history of delayed payments on loan accounts")
    if has_short_history:
        issues.append("thin credit file (less than 24 months of history)")
    if has_too_many_inquiries:
        # Clarify that this is about inquiries, not utilization
        issues.append(f"excessive credit seeking ({inquiry_count} bank inquiries detected in last 90 days)")
    if has_poor_mix:
        issues.append("unbalanced debt profile (100% unsecured credit cards)")

    # --- 5. Use Gemini AI for Personalized Roadmap (if API key is set) ---
    red_flags = []
    was_ai_successful = False
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'")
    
    if gemini_api_key and gemini_api_key != "your-api-key-here" and issues:
        try:
            issues_text = "\n".join(f"- {issue}" for issue in issues)
            prompt = f"""You are a senior Malaysian SME financial advisor at a top-tier bank like Maybank or CIMB.

BUSINESS PROFILE:
- Business: {business_name}
- CTOS Credit Score: {score} / 850 (Grade: {grade})
- Credit Utilization: {utilization_pct}% on revolving credit facilities
- Monthly Revenue: RM {monthly_revenue:,} (avg over last 6 months)
- Cash on Hand: RM {cash_on_hand:,}
- Target Loan Amount: RM {target_loan:,} (working capital expansion)
- Loan Probability: {prob}%

DETECTED CREDIT ISSUES:
{issues_text}

TASK:
For EACH credit issue above, generate a JSON object with HIGHLY SPECIFIC advice using real RM amounts, exact percentages, and concrete timeframes. Do NOT give generic advice.

Each JSON object must have exactly these 4 keys:
- "type": A concise title for the issue (e.g. "High Credit Utilization at {utilization_pct}%")
- "description": 2 sentences. Explain specifically what the issue is, what metric triggered it, and how it is currently impacting the credit score and the RM {target_loan:,} loan application.
- "roadmap_action": A numbered 2-step action plan with SPECIFIC RM amounts, bank names or methods, and exact timeframe (e.g. "Step 1: Within the next 30 days, pay down RM X from your Maybank credit card to bring utilization from {utilization_pct}% to below 30%. Step 2: Set up a CIMB auto-debit instruction to ensure minimum monthly payments are never missed.")
- "roadmap_impact": State the expected score points gained, the timeframe for improvement, and how this improves the RM {target_loan:,} loan outcome.
- "loan_approval_prediction": A percentage (0-100) representing the likelihood of approval for the RM {target_loan:,} loan. USE THE CALCULATED 'Loan Probability' ({prob}%) AS YOUR ABSOLUTE BASELINE. Do NOT give a high percentage if the baseline is low.

Return ONLY a raw JSON array. No markdown, no code blocks, no explanation."""

            # Detect OpenAI key vs Google key
            if gemini_api_key.startswith("sk-"):
                from openai import OpenAI
                client = OpenAI(api_key=gemini_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o", # Default to gpt-4o for OpenAI keys
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" } if False else None # Optional: ensure json if model supports it
                )
                raw = response.choices[0].message.content.strip()
            else:
                client = google_genai.Client(api_key=gemini_api_key)
                print(f"DEBUG: Generating AI recommendation for {business_name} using gemini-2.5-flash...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash", # Updated to a valid model in this environment
                    contents=prompt
                )
                raw = response.text.strip()
                print(f"DEBUG: Gemini raw response received (length: {len(raw)})")

            # Log raw response for debugging
            log_dir = Path(__file__).parent.parent.parent / "logs"
            os.makedirs(log_dir, exist_ok=True)
            with open(log_dir / "gemini_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now()} ---\n")
                f.write(f"MODEL: gemini-2.5-flash\n")
                f.write(f"RAW RESPONSE: {raw}\n")

            # Clean up response (strip markdown)
            if raw.startswith("```"):
                parts = raw.split("```")
                if len(parts) > 1:
                    raw = parts[1]
                    if raw.strip().startswith("json"):
                        raw = raw.strip()[4:]
            
            try:
                # Extra cleanup - remove any leading/trailing non-JSON characters if they exist
                raw_json = raw.strip()
                if "[" in raw_json and "]" in raw_json:
                     start = raw_json.find("[")
                     end = raw_json.rfind("]") + 1
                     raw_json = raw_json[start:end]
                
                red_flags = _json.loads(raw_json)
                was_ai_successful = True
            except Exception as json_err:
                print(f"JSON PARSE ERROR: {json_err}")
                if log_dir:
                    with open(log_dir / "gemini_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"JSON PARSE ERROR: {json_err}\n")
                raise json_err # trigger critical error catch below

        except Exception as e:
            error_msg = f"CRITICAL Gemini API error: {type(e).__name__}: {e}"
            print(error_msg)
            # Log to dedicated file for user to see
            log_dir = Path(__file__).parent.parent.parent / "logs"
            os.makedirs(log_dir, exist_ok=True)
            with open(log_dir / "gemini_errors.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now()}] {error_msg}\n")
            with open(log_dir / "gemini_debug.log", "a", encoding="utf-8") as f:
                f.write(f"EXCEPTION: {error_msg}\n")
            red_flags = None  # trigger fallback
            was_ai_successful = False

    # --- 6. Fallback: Rules-Based Engine (Enhanced with Real Data) ---
    if not red_flags and issues:
        was_ai_successful = False
        red_flags = []
        if utilization_pct > 50:
            debt_rm = round(monthly_revenue * (utilization_pct / 100))
            red_flags.append({
                "type": f"High Credit Utilization ({utilization_pct}%)", 
                "description": f"Your current revolving debt is estimated at RM {debt_rm:,}. This is significantly impacting your RM {target_loan:,} loan capacity.",
                "roadmap_action": f"Within 30 days, pay down RM {round(max(0, debt_rm * 0.4)):,} to bring utilization below the 30% healthy threshold.", 
                "roadmap_impact": "Will add approximately 25-40 points to your CTOS score within 2 billing cycles."
            })
        if has_delayed_payment:
            red_flags.append({
                "type": "Historical Delayed Payment", 
                "description": "Records indicate missed payments that occurred during low cash flow months.",
                "roadmap_action": f"Use your current cash on hand (RM {max(0, cash_on_hand):,}) to settle any outstanding arrears immediately and set up auto-debit.", 
                "roadmap_impact": "Stabilizes your profile; 6 months of consistent payment will unlock Tier 1 bank rates."
            })
        if has_short_history:
            red_flags.append({
                "type": "Thin Credit File", 
                "description": f"Business age is insufficient for high-limit financing (RM {target_loan:,}).",
                "roadmap_action": "Maintain your existing facilities and ensure consistent monthly revenue reporting to CTOS/CCRIS.", 
                "roadmap_impact": "Time-based improvement; score will naturally rise as your business reaches the 24-month mark."
            })
        if has_too_many_inquiries:
            red_flags.append({
                "type": "Excessive Credit Seeking", 
                "description": "Multiple bank inquiries detected in a short window signaling high urgency/risk.",
                "roadmap_action": "Cease all new credit applications for the next 180 days to allow inquiry flags to reset.", 
                "roadmap_impact": "Reduces risk profile and can recover 10-15 points almost immediately."
            })
        if has_poor_mix:
            red_flags.append({
                "type": "Unbalanced Debt Mix", 
                "description": "Your profile relies heavily on unsecured credit, which is considered high-risk for expansion loans.",
                "roadmap_action": f"Consider converting RM {round(max(0, cash_on_hand * 0.2)):,} of short-term debt into a secured term loan.", 
                "roadmap_impact": "Demonstrates sophisticated debt management and improves long-term bankability.",
                "loan_approval_prediction": prob
            })

    return {
        "score": int(score),
        "grade": grade,
        "loan_probability": float(prob),
        "bank_decision": decision,
        "elements": elements,
        "red_flags": red_flags or [],
        "ai_powered": was_ai_successful
    }

@router.post("/api/payments/scan-receipt")
async def scan_receipt(file: dict = None):
    # Simulated OCR extraction
    return {
        "extracted_data": {
            "amount": 2500.0,
            "currency": "MYR",
            "reference_number": "REF-882-991",
            "transaction_date": "2025-03-04",
            "sender_name": "ABC Corp"
        },
        "suggested_matches": [
            {"id": 1, "invoice_number": "INV-2025-001", "total_amount": 2500.0, "status": "unpaid", "client_id": 1}
        ]
    }

@router.post("/api/payments/verify")
async def verify_payment(data: dict):
    return {"status": "success", "payment": {"id": "PAY-9932"}}

@router.post("/api/ssm/register")
async def ssm_register(details: dict):
    return {"status": "success", "ref_no": "SSM-DB-8832"}

@router.post("/api/ssm/annual-return")
async def ssm_annual_return(data: dict):
    return {
        "status": "success",
        "reference_id": "SSM-AR-2026-9821",
        "message": "Annual Return has been filed successfully."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
