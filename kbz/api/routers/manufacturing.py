from fastapi import APIRouter, Depends, Request

from ..schemas import BomIn, WorkOrderIn, CompleteProductionIn
from .deps import get_ctx

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])


@router.get("/boms")
def list_boms(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.list_boms(ctx)


@router.post("/boms", status_code=201)
def create_bom(body: BomIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.create_bom(
        ctx, body.product_id, [c.model_dump() for c in body.components], body.version)


@router.get("/boms/{bom_id}")
def get_bom(bom_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.get_bom(ctx, bom_id)


@router.get("/boms/{bom_id}/explode")
def explode(bom_id: str, qty: float, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.explode(ctx, bom_id, qty)


@router.get("/work-orders")
def list_wos(status: str | None = None, request: Request = None, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.list_work_orders(ctx, status=status)


@router.post("/work-orders", status_code=201)
def create_wo(body: WorkOrderIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.create_work_order(
        ctx, body.bom_id, body.qty_planned, body.notes)


@router.get("/work-orders/{wo_id}")
def get_wo(wo_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.get_work_order(ctx, wo_id)


@router.post("/work-orders/{wo_id}/start")
def start_wo(wo_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.start_work_order(ctx, wo_id)


@router.post("/work-orders/{wo_id}/complete")
def complete_wo(wo_id: str, body: CompleteProductionIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.manufacturing.complete_production(ctx, wo_id, body.qty_produced)
