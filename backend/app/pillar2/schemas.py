"""
Pydantic schemas for Pillar 2 invoice pre-vet (Schema Enforcement).
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class Vendor(BaseModel):
    name: str
    address: str
    country: str = Field(..., min_length=2, max_length=2)


class Buyer(BaseModel):
    name: str
    address: str
    country: str = Field(..., min_length=2, max_length=2)


class LineItem(BaseModel):
    item_id: int
    description: str
    quantity: int | float = Field(..., gt=0)
    unit: str
    unit_price: float | Decimal = Field(..., ge=0)
    amount: float | Decimal = Field(..., ge=0)
    origin_country: str = Field(..., min_length=2, max_length=2)


class Invoice(BaseModel):
    invoice_id: str
    invoice_date: str  # YYYY-MM-DD
    vendor: Vendor
    buyer: Buyer
    line_items: list[LineItem]
    subtotal: float | Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    notes: str | None = None


class ClassifiedLineItem(BaseModel):
    item_id: int
    description: str
    quantity: int | float
    unit: str
    unit_price: float
    amount: float
    origin_country: str
    ahtn_code: str
    ahtn_description: str
    tariff_rate: str
    tariff_amount: float
    similarity: float
    requires_hitl: bool
    flags: list[str] = Field(default_factory=list)


class PreVetResult(BaseModel):
    invoice_id: str
    line_items: list[ClassifiedLineItem]
    total_tariff: float
    currency: str
    any_requires_hitl: bool
    all_flags: list[str] = Field(default_factory=list)
