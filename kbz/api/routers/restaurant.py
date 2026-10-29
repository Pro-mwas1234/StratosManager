from fastapi import APIRouter, Depends, Request

from ..schemas import MenuItemIn, TableIn, OpenOrderIn, OrderItemIn, CloseOrderIn
from .deps import get_ctx

router = APIRouter(prefix="/restaurant", tags=["restaurant"])


@router.get("/menu")
def list_menu(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.list_menu(ctx)


@router.post("/menu", status_code=201)
def add_menu_item(body: MenuItemIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.add_menu_item(
        ctx, body.name, body.price_cents, body.category, body.product_id)


@router.get("/tables")
def list_tables(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.list_tables(ctx)


@router.post("/tables", status_code=201)
def add_table(body: TableIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.add_table(ctx, body.label, body.seats)


@router.get("/orders")
def list_orders(status: str | None = None, request: Request = None, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.list_orders(ctx, status=status)


@router.post("/orders", status_code=201)
def open_order(body: OpenOrderIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.open_order(ctx, body.table_id)


@router.get("/orders/{order_id}")
def get_order(order_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.get_order(ctx, order_id)


@router.post("/orders/{order_id}/items", status_code=201)
def add_item(order_id: str, body: OrderItemIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.add_order_item(
        ctx, order_id, body.menu_item_id, body.qty, body.notes)


@router.post("/orders/{order_id}/close")
def close_order(order_id: str, body: CloseOrderIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.restaurant.close_order(ctx, order_id, body.payment_method)


@router.get("/orders/{order_id}/kitchen-ticket")
def kitchen_ticket(order_id: str, request: Request, ctx=Depends(get_ctx)):
    return {"ticket": request.app.state.kbz.restaurant.kitchen_ticket(ctx, order_id)}
