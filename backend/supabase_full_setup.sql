-- FinanceFlow (Ctrl-Z) — Full Supabase Schema Setup
-- Run this script in the Supabase SQL Editor (https://supabase.com/dashboard/project/_/sql)
-- This script creates all necessary tables, constraints, and functions for the project.

-- 0. Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create user_companies (Base table for multi-tenancy)
CREATE TABLE IF NOT EXISTS public.user_companies (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id text NOT NULL, -- Ties to Auth UID or Clerk ID
  name text NOT NULL,
  address text,
  business_reg text,
  logo_url text,
  created_at timestamp with time zone DEFAULT now(),
  base_currency text DEFAULT 'MYR'::text,
  email text,
  compliance_status text, -- Stores year of last tax submission
  CONSTRAINT user_companies_pkey PRIMARY KEY (id)
);

-- 2. Create clients
CREATE TABLE IF NOT EXISTS public.clients (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  company_id uuid,
  name text NOT NULL,
  contact_info text,
  business_reg text,
  person_in_charge text,
  type text CHECK (type = ANY (ARRAY['customer'::text, 'supplier'::text])),
  phone_number text,
  address text,
  country varchar(2),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT clients_pkey PRIMARY KEY (id),
  CONSTRAINT clients_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.user_companies(id) ON DELETE CASCADE
);

-- 3. Create products
CREATE TABLE IF NOT EXISTS public.products (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  company_id uuid,
  supplier_id uuid,
  name text NOT NULL,
  price numeric DEFAULT 0.0,
  cost_price numeric DEFAULT 0.0,
  currency text DEFAULT 'MYR'::text,
  inventory integer NOT NULL DEFAULT 0,
  threshold integer NOT NULL DEFAULT 10,
  unit varchar(20),
  origin_country varchar(2),
  image text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT products_pkey PRIMARY KEY (id),
  CONSTRAINT products_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.user_companies(id) ON DELETE CASCADE,
  CONSTRAINT products_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.clients(id) ON DELETE SET NULL
);

-- 4. Create invoices
CREATE TABLE IF NOT EXISTS public.invoices (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  client_id uuid,
  invoice_number text NOT NULL,
  date date NOT NULL,
  month text NOT NULL,
  status text DEFAULT 'unpaid'::text CHECK (status = ANY (ARRAY['unpaid'::text, 'paid'::text, 'partially_paid'::text])),
  total_amount numeric DEFAULT 0,
  currency text DEFAULT 'MYR'::text,
  exchange_rate numeric DEFAULT 1.0,
  tariff numeric DEFAULT 0,
  type text DEFAULT 'issuing'::text CHECK (type = ANY (ARRAY['issuing'::text, 'receiving'::text])),
  ai_auto_paid_reason text,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT invoices_pkey PRIMARY KEY (id),
  CONSTRAINT invoices_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE
);

-- 5. Create invoice_items
CREATE TABLE IF NOT EXISTS public.invoice_items (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  invoice_id uuid,
  product_id uuid,
  description text NOT NULL,
  price numeric NOT NULL,
  unit_price numeric,
  quantity integer NOT NULL,
  subtotal numeric GENERATED ALWAYS AS (price * quantity) STORED,
  unit varchar(20),
  origin_country varchar(2),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT invoice_items_pkey PRIMARY KEY (id),
  CONSTRAINT invoice_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE,
  CONSTRAINT invoice_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL
);

-- 6. Create payments
CREATE TABLE IF NOT EXISTS public.payments (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  client_id uuid,
  amount numeric NOT NULL,
  date date NOT NULL,
  method text,
  notes text,
  currency text DEFAULT 'MYR'::text,
  exchange_rate numeric DEFAULT 1.0,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT payments_pkey PRIMARY KEY (id),
  CONSTRAINT payments_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE
);

-- 7. Create staff
CREATE TABLE IF NOT EXISTS public.staff (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  company_id uuid,
  name text NOT NULL UNIQUE,
  email text UNIQUE,
  role text,
  salary numeric,
  epf_rate numeric DEFAULT 0.13,
  socso_rate numeric DEFAULT 0.0175,
  eis_rate numeric DEFAULT 0.002,
  tax_rate numeric DEFAULT 0,
  epf numeric, -- Absolute fallback
  socso numeric,
  eis numeric,
  tax numeric,
  nric text,
  dob text,
  nationality text,
  address text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT staff_pkey PRIMARY KEY (id),
  CONSTRAINT staff_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.user_companies(id) ON DELETE CASCADE
);

-- 8. Create invoice_prevet_results (For HITL Liability Shield)
CREATE TABLE IF NOT EXISTS public.invoice_prevet_results (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  invoice_id text NOT NULL,
  invoice_data jsonb NOT NULL,
  pre_vet_result jsonb NOT NULL,
  source_file text,
  status text NOT NULL DEFAULT 'pending_review'::text CHECK (status = ANY (ARRAY['pending_review'::text, 'approved'::text])),
  reviewed_by text,
  reviewed_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT invoice_prevet_results_pkey PRIMARY KEY (id)
);

-- 9. Create whatsapp_messages (For Bot Session Tracking)
CREATE TABLE IF NOT EXISTS public.whatsapp_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id text NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  intent text,
  mood text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT whatsapp_messages_pkey PRIMARY KEY (id)
);

-- 10. Create Additional Utility Tables
CREATE TABLE IF NOT EXISTS public.pending_invoices (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id text NOT NULL,
  raw_message text,
  extracted_data jsonb,
  missing_fields jsonb,
  last_interaction timestamp with time zone DEFAULT now(),
  CONSTRAINT pending_invoices_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.instagram_posts (
  id text NOT NULL,
  caption text,
  likes_count integer,
  comments_count integer,
  fetched_at timestamp with time zone DEFAULT now(),
  CONSTRAINT instagram_posts_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.instagram_comments (
  id text NOT NULL,
  post_id text,
  username text,
  text text,
  sentiment text,
  ai_reply text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT instagram_comments_pkey PRIMARY KEY (id)
);

-- 11. Stored Procedures
-- Utility for atomic inventory updates
CREATE OR REPLACE FUNCTION public.adjust_inventory(p_product_id uuid, p_delta integer)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
  new_val integer;
BEGIN
  UPDATE public.products
  SET inventory = GREATEST(0, inventory + p_delta),
      updated_at = now()
  WHERE id = p_product_id
  RETURNING inventory INTO new_val;
  RETURN new_val;
END;
$$;

-- 12. Row Level Security (RLS) - Recommendations
-- By default, Supabase tables are public if RLS is not enabled. 
-- For a production environment, you should enable RLS and create policies.
-- ALTER TABLE public.user_companies ENABLE ROW LEVEL SECURITY;
-- ... and so on.
