"""Pydantic input models for the REST API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str
    password: str
    tenant_name: str
    kra_pin: str | None = None
    phone: str | None = None
    plan_id: str = "starter"


class LoginIn(BaseModel):
    email: str
    password: str


class StaffIn(BaseModel):
    email: str
    password: str


class CustomerIn(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    kra_pin: str | None = None
    address: str | None = None


class InvoiceLineIn(BaseModel):
    description: str
    qty: float = 1
    unit_price_cents: int = Field(ge=0)
    vat_rate: float = 0.16


class InvoiceIn(BaseModel):
    customer_id: str | None = None
    lines: list[InvoiceLineIn]
    due_date: str | None = None
    notes: str | None = None
    inclusive_vat: bool = False


class PaymentIn(BaseModel):
    amount_cents: int = Field(gt=0)
    method: str = "MPESA"
    reference: str | None = None


class ProductIn(BaseModel):
    sku: str
    name: str
    sale_price_cents: int = Field(ge=0)
    cost_price_cents: int = Field(default=0, ge=0)
    category: str | None = None
    vat_exempt: bool = False
    reorder_level: int = 0


class StockAdjustIn(BaseModel):
    delta: int
    reason: str = "adjustment"
    ref: str | None = None


class SaleItemIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)


class SaleIn(BaseModel):
    items: list[SaleItemIn]
    payment_method: str = "CASH"
    mpesa_ref: str | None = None
    cashier: str | None = None


class MenuItemIn(BaseModel):
    name: str
    price_cents: int = Field(ge=0)
    category: str | None = None
    product_id: str | None = None


class TableIn(BaseModel):
    label: str
    seats: int = 4


class OrderItemIn(BaseModel):
    menu_item_id: str
    qty: int = Field(gt=0, default=1)
    notes: str | None = None


class OpenOrderIn(BaseModel):
    table_id: str | None = None


class CloseOrderIn(BaseModel):
    payment_method: str = "MPESA"


class RoomIn(BaseModel):
    number: str
    rate_cents: int = Field(ge=0)
    room_type: str = "standard"


class BookingIn(BaseModel):
    guest_name: str
    guest_phone: str | None = None
    room_id: str
    check_in: str
    check_out: str


class PropertyIn(BaseModel):
    name: str
    location: str | None = None


class UnitIn(BaseModel):
    property_id: str
    label: str
    rent_cents: int = Field(ge=0)


class LeaseIn(BaseModel):
    unit_id: str
    tenant_name: str
    tenant_phone: str | None = None
    start_date: str
    end_date: str
    rent_cents: int | None = None
    deposit_cents: int = 0


class RentBillIn(BaseModel):
    lease_id: str
    period: str | None = None
    due_day: int = 10


class RentPaymentIn(BaseModel):
    amount_cents: int = Field(gt=0)
    method: str = "MPESA"
    reference: str | None = None


class BomComponentIn(BaseModel):
    product_id: str
    qty: float = Field(gt=0)


class BomIn(BaseModel):
    product_id: str
    components: list[BomComponentIn]
    version: str = "v1"


class WorkOrderIn(BaseModel):
    bom_id: str
    qty_planned: float = Field(gt=0)
    notes: str | None = None


class CompleteProductionIn(BaseModel):
    qty_produced: float = Field(gt=0)


class SubscribeIn(BaseModel):
    plan_id: str
