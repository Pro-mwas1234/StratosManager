from fastapi import APIRouter, Depends, Request

from ..schemas import ProductIn, StockAdjustIn, SaleIn
from .deps import get_ctx

router = APIRouter(prefix="/retail", tags=["retail"])


@router.get("/products")
def list_products(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.list_products(ctx)


@router.post("/products", status_code=201)
def create_product(body: ProductIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.create_product(
        ctx, body.sku, body.name, body.sale_price_cents, body.cost_price_cents,
        body.category, body.vat_exempt, body.reorder_level)


@router.get("/products/{product_id}")
def get_product(product_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.get_product(ctx, product_id)


@router.post("/products/{product_id}/stock")
def adjust_stock(product_id: str, body: StockAdjustIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.adjust_stock(ctx, product_id, body.delta, body.reason, body.ref)


@router.get("/stock/low")
def low_stock(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.low_stock(ctx)


@router.get("/sales")
def list_sales(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.list_sales(ctx)


@router.post("/sales", status_code=201)
def create_sale(body: SaleIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.create_sale(
        ctx, [i.model_dump() for i in body.items], body.payment_method, body.mpesa_ref, body.cashier)


@router.get("/summary/today")
def today(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.retail.daily_summary(ctx)
