"""
Pydantic models for request/response validation.
"""

from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────
# Company
# ──────────────────────────────────────
class CompanyCreate(BaseModel):
    name: str
    address: Optional[str] = None
    business_reg: Optional[str] = None
    logo_url: Optional[str] = None
    base_currency: str = "MYR"


class CompanyOut(CompanyCreate):
    id: str
    user_id: str
    created_at: datetime


# ──────────────────────────────────────
# Client
# ──────────────────────────────────────
class ClientCreate(BaseModel):
    company_id: Optional[str] = None
    name: str
    contact_info: Optional[str] = None
    phone_number: Optional[str] = None
    business_reg: Optional[str] = None
    person_in_charge: Optional[str] = None
    type: Optional[str] = Field(None, pattern="^(customer|supplier)$")
    address: Optional[str] = None
    country: Optional[str] = None  # ISO 2-letter code (e.g., "MY", "SG", "ID")


class ClientOut(ClientCreate):
    id: str
    created_at: datetime


# ──────────────────────────────────────
# Invoice
# ──────────────────────────────────────
class InvoiceItemCreate(BaseModel):
    description: str
    price: Decimal
    quantity: int
    unit: Optional[str] = None
    origin_country: Optional[str] = None
    unit_price: Optional[Decimal] = None


class InvoiceCreate(BaseModel):
    client_id: str
    invoice_number: str
    date: date
    month: str
    type: str = Field("issuing", pattern="^(issuing|receiving)$")
    currency: str = "MYR"
    exchange_rate: Decimal = Decimal("1.0")
    tariff: Decimal = Decimal("0.0")
    items: list[InvoiceItemCreate]
    notes: Optional[str] = None


class InvoiceItemOut(BaseModel):
    id: str
    invoice_id: str
    product_id: Optional[str] = None
    description: str
    price: Decimal
    quantity: int
    subtotal: Decimal
    created_at: datetime
    unit: Optional[str] = None
    origin_country: Optional[str] = None
    unit_price: Optional[Decimal] = None


class InvoiceOut(BaseModel):
    id: str
    client_id: str
    invoice_number: str
    date: date
    month: str
    status: str
    total_amount: Decimal
    type: str = "issuing"
    currency: str = "MYR"
    exchange_rate: Decimal = Decimal("1.0")
    tariff: Decimal = Decimal("0.0")
    created_at: datetime
    items: list[InvoiceItemOut] = []
    client_name: Optional[str] = None
    ai_auto_paid_reason: Optional[str] = None
    notes: Optional[str] = None


class InvoiceStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(unpaid|paid|partially_paid)$")


# ──────────────────────────────────────
# Payment
# ──────────────────────────────────────
class PaymentCreate(BaseModel):
    client_id: str
    amount: Decimal
    date: date
    method: Optional[str] = None
    notes: Optional[str] = None
    currency: str = "MYR"
    exchange_rate: Decimal = Decimal("1.0")


class PaymentOut(PaymentCreate):
    id: str
    created_at: datetime


# ──────────────────────────────────────
# AI / WhatsApp
# ──────────────────────────────────────
class WhatsAppMessage(BaseModel):
    phone_number: str
    message: str


class AIExtractionResult(BaseModel):
    status: str  # "complete" | "incomplete"
    data: dict
    questions: list[str] = []


# ──────────────────────────────────────
# Net Balance
# ──────────────────────────────────────
class NetBalanceOut(BaseModel):
    client_id: str
    client_name: str
    month: str
    total_invoiced: Decimal
    total_paid: Decimal
    net_balance: Decimal


# ──────────────────────────────────────
# OCR / Receipt Parsing
# ──────────────────────────────────────
class ReceiptExtractionResult(BaseModel):
    transaction_date: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = "MYR"
    reference_number: Optional[str] = None
    sender_name: Optional[str] = None
    bank_name: Optional[str] = None


class PaymentVerificationRequest(BaseModel):
    invoice_id: str
    client_id: str
    amount: Decimal
    date: date
    method: Optional[str] = None
    notes: Optional[str] = None
    currency: str = "MYR"
    exchange_rate: Decimal = Decimal("1.0")


class FinancialSummaryOut(BaseModel):
    cash_on_hand: Decimal
    total_assets: Decimal
    available_for_expenses: Decimal
    base_currency: str = "MYR"
    client_pending: list[dict]
    supplier_pending: list[dict]
