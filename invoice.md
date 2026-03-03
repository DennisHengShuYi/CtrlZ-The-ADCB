# Implementation Plan: AI-Powered WhatsApp Invoice Generation

## 1. Database Schema (Supabase SQL)
```sql
-- Create User Companies table
CREATE TABLE user_companies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users NOT NULL,
  name TEXT NOT NULL,
  address TEXT,
  business_reg TEXT,
  logo_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for User Companies
ALTER TABLE user_companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only see their own company" ON user_companies
  FOR ALL USING (auth.uid() = user_id);

-- Create Clients table
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES user_companies(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact_info TEXT,
  business_reg TEXT,
  person_in_charge TEXT,
  type TEXT CHECK (type IN ('customer', 'supplier')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Clients
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only see their company's clients" ON clients
  FOR ALL USING (
    company_id IN (SELECT id FROM user_companies WHERE user_id = auth.uid())
  );

-- Create Invoices table
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  invoice_number TEXT NOT NULL,
  date DATE NOT NULL,
  month TEXT NOT NULL,
  status TEXT DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'paid', 'partially_paid')),
  total_amount DECIMAL(12,2) DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Invoices
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only see their company's invoices" ON invoices
  FOR ALL USING (
    client_id IN (
      SELECT id FROM clients WHERE company_id IN (
        SELECT id FROM user_companies WHERE user_id = auth.uid()
      )
    )
  );

-- Create Invoice Items table
CREATE TABLE invoice_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  price DECIMAL(12,2) NOT NULL,
  quantity INTEGER NOT NULL,
  subtotal DECIMAL(12,2) GENERATED ALWAYS AS (price * quantity) STORED,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Invoice Items
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only see their company's invoice items" ON invoice_items
  FOR ALL USING (
    invoice_id IN (
      SELECT id FROM invoices WHERE client_id IN (
        SELECT id FROM clients WHERE company_id IN (
          SELECT id FROM user_companies WHERE user_id = auth.uid()
        )
      )
    )
  );

-- Create Payments table
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  amount DECIMAL(12,2) NOT NULL,
  date DATE NOT NULL,
  method TEXT,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Payments
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only see their company's payments" ON payments
  FOR ALL USING (
    client_id IN (
      SELECT id FROM clients WHERE company_id IN (
        SELECT id FROM user_companies WHERE user_id = auth.uid()
      )
    )
  );

-- Create Pending Invoices table for AI conversational state
CREATE TABLE pending_invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users NOT NULL,
  raw_message TEXT,
  extracted_data JSONB, -- { "client_name": "...", "items": [...], "date": "..." }
  missing_fields TEXT[], -- e.g. ["price", "quantity"]
  last_interaction TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE pending_invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only see their own pending invoices" ON pending_invoices
  FOR ALL USING (auth.uid() = user_id);
```

## 2. AI Prompt Logic for WhatsApp Data Extraction

**System Prompt for AI (e.g., Gemini 2.0 Flash):**
```text
You are an expert invoice assistant for FinanceFlow. 
Your task is to extract invoice details from WhatsApp messages. 

Required Fields:
1. Client Name (e.g., "ABC Corp")
2. Invoice Date (YYYY-MM-DD format)
3. Invoice Month (e.g., "March 2024")
4. Items: List of objects containing { description, price, quantity }

Rules:
- If a field is missing or ambiguous, you MUST identify it.
- If the message says "ABC Corp 5 laptops at 1000 each", extract Client: "ABC Corp", Item: "laptops", Qty: 5, Price: 1000.
- If the user only says "I want to create an invoice for ABC Corp for 5 laptops", ask for the price.

Output Format (JSON):
{
  "status": "complete" | "incomplete",
  "data": {
    "client_name": string | null,
    "date": string | null,
    "month": string | null,
    "items": Array<{ description: string, price: number, quantity: number }>
  },
  "questions": string[] // List of questions to ask the user to fill missing data
}
```

## 3. Conversational Workflow (WhatsApp Integration)

1.  **User sends message to WhatsApp.**
2.  **Webhook Triggered**: FastAPI receives the message and identifies the user (e.g., via phone number linked to `auth.users`).
3.  **AI Analysis**: LLM processes the message using the prompt above.
4.  **Conditional logic**:
    - **IF `status == "incomplete"`**: 
        - Store `data` in `pending_invoices`.
        - Send the first question from `questions` back to the user via WhatsApp.
    - **IF `status == "complete"`**:
        - Search for `client_name` in the `clients` table.
        - If client exists, proceed. If not, ask the user if they want to create a new client first.
        - Once confirmed, insert record into `invoices` and `invoice_items`.
        - Calculate `total_amount` for the invoice.
        - Generate PDF (using ReportLab/WeasyPrint).
        - Send PDF download link back to WhatsApp.

## 4. Net Balance Logic (Monthly Statement)

To calculate the net balance for a client for a specific month:
- **Debits**: Sum of all invoices (`total_amount`) where `month` matches.
- **Credits**: Sum of all payments (`amount`) where the payment date falls within that month.
- **Net Balance**: `Total Debits - Total Credits`.

**SQL Query Helper:**
```sql
SELECT 
  (SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE client_id = $1 AND month = $2) -
  (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE client_id = $1 AND TO_CHAR(date, 'YYYY-MM') = $3) 
AS net_balance;
```

## 5. Next Steps
1.  **Backend**: Add `supabase-py` and `google-generativeai` to `requirements.txt`.
2.  **Backend**: Implement `/api/whatsapp/webhook` endpoint.
3.  **Frontend**: Create a "WhatsApp Configuration" page to link phone numbers.
4.  **PDF Service**: Implement a PDF template that matches the company's profile (logo, address).
