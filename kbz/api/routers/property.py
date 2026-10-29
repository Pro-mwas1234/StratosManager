from fastapi import APIRouter, Depends, Request

from ..schemas import PropertyIn, UnitIn, LeaseIn, RentBillIn, RentPaymentIn
from .deps import get_ctx

router = APIRouter(prefix="/property", tags=["property"])


@router.get("/properties")
def list_properties(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.list_properties(ctx)


@router.post("/properties", status_code=201)
def add_property(body: PropertyIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.add_property(ctx, body.name, body.location)


@router.post("/units", status_code=201)
def add_unit(body: UnitIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.add_unit(ctx, body.property_id, body.label, body.rent_cents)


@router.get("/leases")
def list_leases(status: str | None = "active", request: Request = None, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.list_leases(ctx, status=status)


@router.post("/leases", status_code=201)
def create_lease(body: LeaseIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.create_lease(
        ctx, body.unit_id, body.tenant_name, body.start_date, body.end_date,
        body.rent_cents, body.deposit_cents, body.tenant_phone)


@router.post("/leases/{lease_id}/end")
def end_lease(lease_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.end_lease(ctx, lease_id)


@router.post("/rent-bills", status_code=201)
def issue_bill(body: RentBillIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.issue_rent_bill(ctx, body.lease_id, body.period, body.due_day)


@router.get("/rent-bills/{bill_id}")
def get_bill(bill_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.get_bill(ctx, bill_id)


@router.post("/rent-bills/{bill_id}/payments")
def pay_bill(bill_id: str, body: RentPaymentIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.record_rent_payment(
        ctx, bill_id, body.amount_cents, body.method, body.reference)


@router.get("/reports/arrears")
def arrears(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.property.arrears_report(ctx)
