from fastapi import APIRouter, Depends, Request

from ..schemas import CustomerIn, InvoiceIn, PaymentIn
from .deps import get_ctx

router = APIRouter(prefix="/invoices", tags=["invoicing"])


@router.get("/customers")
def list_customers(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.list_customers(ctx)


@router.post("/customers", status_code=201)
def create_customer(body: CustomerIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.create_customer(
        ctx, body.name, body.email, body.phone, body.kra_pin, body.address)


@router.get("/reports/aging")
def aging(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.aging_report(ctx)


@router.get("/")
def list_invoices(status: str | None = None, request: Request = None, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.list_invoices(ctx, status=status)


@router.post("/", status_code=201)
def create_invoice(body: InvoiceIn, request: Request, ctx=Depends(get_ctx)):
    lines = [l.model_dump() for l in body.lines]
    return request.app.state.kbz.invoicing.create_invoice(
        ctx, lines, customer_id=body.customer_id, due_date=body.due_date,
        notes=body.notes, inclusive_vat=body.inclusive_vat)


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.get_invoice(ctx, invoice_id)


@router.post("/{invoice_id}/payments")
def record_payment(invoice_id: str, body: PaymentIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.record_payment(
        ctx, invoice_id, body.amount_cents, body.method, body.reference)


@router.post("/{invoice_id}/void")
def void_invoice(invoice_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.invoicing.void_invoice(ctx, invoice_id)
