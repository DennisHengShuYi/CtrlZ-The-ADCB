-- =====================================================
-- AI-Powered WhatsApp Invoice Generation — DB Schema
-- Run this in the Supabase SQL Editor
-- =====================================================

-- Create User Companies table
CREATE TABLE IF NOT EXISTS user_companies (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  address TEXT,
  business_reg TEXT,
  logo_url TEXT,
  base_currency TEXT DEFAULT 'MYR',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for User Companies
ALTER TABLE user_companies ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can only see their own company" ON user_companies;
CREATE POLICY "Users can only see their own company" ON user_companies
  FOR ALL USING (auth.uid()::text = user_id::text);

-- Create Clients table
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  company_id UUID REFERENCES user_companies(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  contact_info TEXT,
  phone_number TEXT,
  business_reg TEXT,
  person_in_charge TEXT,
  type TEXT CHECK (type IN ('customer', 'supplier')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Clients
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can only see their company's clients" ON clients;
CREATE POLICY "Users can only see their company's clients" ON clients
  FOR ALL USING (
    company_id IN (SELECT id FROM user_companies WHERE user_id::text = auth.uid()::text)
  );

-- Create Invoices table
CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  invoice_number TEXT NOT NULL,
  date DATE NOT NULL,
  month TEXT NOT NULL,
  type TEXT DEFAULT 'issuing' CHECK (type IN ('issuing', 'receiving')),
  ai_auto_paid_reason TEXT,
  status TEXT DEFAULT 'unpaid' CHECK (status IN ('unpaid', 'paid', 'partially_paid')),
  total_amount DECIMAL(12,2) DEFAULT 0,
  currency TEXT DEFAULT 'MYR',
  exchange_rate DECIMAL(12,6) DEFAULT 1.0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Invoices
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can only see their company's invoices" ON invoices;
CREATE POLICY "Users can only see their company's invoices" ON invoices
  FOR ALL USING (
    client_id IN (
      SELECT id FROM clients WHERE company_id IN (
        SELECT id FROM user_companies WHERE user_id::text = auth.uid()::text
      )
    )
  );

-- Create Invoice Items table
CREATE TABLE IF NOT EXISTS invoice_items (
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
DROP POLICY IF EXISTS "Users can only see their company's invoice items" ON invoice_items;
CREATE POLICY "Users can only see their company's invoice items" ON invoice_items
  FOR ALL USING (
    invoice_id IN (
      SELECT id FROM invoices WHERE client_id IN (
        SELECT id FROM clients WHERE company_id IN (
          SELECT id FROM user_companies WHERE user_id::text = auth.uid()::text
        )
      )
    )
  );

-- Create Payments table
CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  amount DECIMAL(12,2) NOT NULL,
  date DATE NOT NULL,
  method TEXT,
  notes TEXT,
  currency TEXT DEFAULT 'MYR',
  exchange_rate DECIMAL(12,6) DEFAULT 1.0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for Payments
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can only see their company's payments" ON payments;
CREATE POLICY "Users can only see their company's payments" ON payments
  FOR ALL USING (
    client_id IN (
      SELECT id FROM clients WHERE company_id IN (
        SELECT id FROM user_companies WHERE user_id::text = auth.uid()::text
      )
    )
  );

-- Create Pending Invoices table for AI conversational state
CREATE TABLE IF NOT EXISTS pending_invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  raw_message TEXT,
  extracted_data JSONB,
  missing_fields TEXT[],
  last_interaction TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE pending_invoices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can only see their own pending invoices" ON pending_invoices;
CREATE POLICY "Users can only see their own pending invoices" ON pending_invoices
  FOR ALL USING (auth.uid()::text = user_id::text);
