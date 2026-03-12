-- Migration: Add tariff column to invoices table
-- Rationale: Persist approved tariff information in the primary invoice table for analytics and PDF generation.

ALTER TABLE public.invoices 
ADD COLUMN IF NOT EXISTS tariff NUMERIC DEFAULT 0;

COMMENT ON COLUMN public.invoices.tariff IS 'Total approved tariff in the invoice original currency';
