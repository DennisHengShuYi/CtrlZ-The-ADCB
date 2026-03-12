-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.clients (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  company_id uuid,
  name text NOT NULL,
  contact_info text,
  business_reg text,
  person_in_charge text,
  type text CHECK (type = ANY (ARRAY['customer'::text, 'supplier'::text])),
  created_at timestamp with time zone DEFAULT now(),
  phone_number text,
  address text,
  country varchar(2),
  CONSTRAINT clients_pkey PRIMARY KEY (id),
  CONSTRAINT clients_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.user_companies(id)
);
CREATE TABLE public.instagram_comments (
  id text NOT NULL,
  post_id text,
  username text,
  text text,
  sentiment text,
  ai_reply text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT instagram_comments_pkey PRIMARY KEY (id)
);
CREATE TABLE public.instagram_posts (
  id text NOT NULL,
  caption text,
  likes_count integer,
  comments_count integer,
  fetched_at timestamp with time zone DEFAULT now(),
  CONSTRAINT instagram_posts_pkey PRIMARY KEY (id)
);
CREATE TABLE public.invoice_items (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  invoice_id uuid,
  product_id uuid,
  description text NOT NULL,
  price numeric NOT NULL,
  quantity integer NOT NULL,
  subtotal numeric DEFAULT (price * (quantity)::numeric),
  created_at timestamp with time zone DEFAULT now(),
  unit varchar(20),
  origin_country varchar(2),
  unit_price numeric,
  CONSTRAINT invoice_items_pkey PRIMARY KEY (id),
  CONSTRAINT invoice_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id),
  CONSTRAINT invoice_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id)
);
CREATE TABLE public.invoice_prevet_results (
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
CREATE TABLE public.invoices (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  client_id uuid,
  invoice_number text NOT NULL,
  date date NOT NULL,
  month text NOT NULL,
  status text DEFAULT 'unpaid'::text CHECK (status = ANY (ARRAY['unpaid'::text, 'paid'::text, 'partially_paid'::text])),
  total_amount numeric DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  currency text DEFAULT 'USD'::text,
  exchange_rate numeric DEFAULT 1.0,
  tariff numeric DEFAULT 0,
  type text DEFAULT 'issuing'::text CHECK (type = ANY (ARRAY['issuing'::text, 'receiving'::text])),
  ai_auto_paid_reason text,
  notes text,
  CONSTRAINT invoices_pkey PRIMARY KEY (id),
  CONSTRAINT invoices_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id)
);
CREATE TABLE public.payments (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  client_id uuid,
  amount numeric NOT NULL,
  date date NOT NULL,
  method text,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  currency text DEFAULT 'USD'::text,
  exchange_rate numeric DEFAULT 1.0,
  CONSTRAINT payments_pkey PRIMARY KEY (id),
  CONSTRAINT payments_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id)
);
CREATE TABLE public.pending_invoices (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id text NOT NULL,
  raw_message text,
  extracted_data jsonb,
  missing_fields ARRAY,
  last_interaction timestamp with time zone DEFAULT now(),
  CONSTRAINT pending_invoices_pkey PRIMARY KEY (id)
);
CREATE TABLE public.products (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  inventory integer NOT NULL DEFAULT 0,
  threshold integer NOT NULL DEFAULT 10,
  image text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  company_id uuid,
  supplier_id uuid,
  price numeric DEFAULT 0.0,
  currency text DEFAULT 'MYR'::text,
  cost_price numeric DEFAULT 0.0,
  unit varchar(20),
  origin_country varchar(2),
  CONSTRAINT products_pkey PRIMARY KEY (id),
  CONSTRAINT products_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.user_companies(id),
  CONSTRAINT products_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.clients(id)
);
CREATE TABLE public.staff (
  id text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  name text NOT NULL DEFAULT ''::text UNIQUE,
  email text NOT NULL DEFAULT ''::text UNIQUE,
  role text DEFAULT ''::text,
  epf_rate numeric,
  tax_rate numeric,
  socso_rate numeric,
  company_id uuid DEFAULT gen_random_uuid(),
  salary numeric,
  eis_rate numeric,
  CONSTRAINT staff_pkey PRIMARY KEY (id),
  CONSTRAINT staff_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.user_companies(id)
);
CREATE TABLE public.user_companies (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_id text NOT NULL,
  name text NOT NULL,
  address text,
  business_reg text,
  logo_url text,
  created_at timestamp with time zone DEFAULT now(),
  base_currency text DEFAULT 'USD'::text,
  email text,
  CONSTRAINT user_companies_pkey PRIMARY KEY (id)
);
CREATE TABLE public.whatsapp_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id text NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  intent text,
  mood text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT whatsapp_messages_pkey PRIMARY KEY (id)
);