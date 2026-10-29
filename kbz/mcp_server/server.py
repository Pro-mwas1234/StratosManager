"""KaziBiz MCP server — AI-agent tools over the same service layer.

Auth model: agents connect with a tenant token supplied via env KBZ_MCP_TOKEN
(deployment-time secret) or per-session header. Tool availability is filtered by
the tenant's plan entitlements; every write goes through the same limit checks, so
an agent cannot do anything the API user could not.

Run:  python -m kbz.mcp_server.server          (stdio transport)
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from ..app import App
from ..core.domain import AuthContext
from ..core.errors import KBZError
from ..core.money import fmt_kes, parse_amount

DB_PATH = os.environ.get("KBZ_DB")
TOKEN = os.environ.get("KBZ_MCP_TOKEN", "")

mcp = FastMCP("kzbiz", instructions=(
    "KaziBiz: multi-tenant business management for Kenyan SMEs. "
    "Tools cover retail POS, invoicing (VAT 16%, M-Pesa refs), restaurant, hotel, "
    "property rental, manufacturing and billing usage. All amounts are KES; pass prices "
    "as decimal strings like '150.00'. Tenant identity comes from the session token."))

_application: App | None = None


def _app() -> App:
    global _application
    if _application is None:
        _application = App(DB_PATH)
    return _application


def _ctx() -> AuthContext:
    if not TOKEN:
        raise KBZError("MCP server has no tenant token (set KBZ_MCP_TOKEN)", code="unauthenticated")
    ctx = _app().users.context_from_token(TOKEN, surface="mcp")
    _app().entitlements.require_feature(ctx.tenant_id, "mcp")
    return ctx


def _wrap(fn):
    """Convert domain errors into tool-level error strings agents can read."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KBZError as e:
            return {"error": {"code": e.code, "message": e.message}}
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# ------------------------------------------------------------------ overview
@mcp.tool()
@_wrap
def kbz_whoami() -> dict:
    """Current tenant, plan and enabled modules. Call this first."""
    a, ctx = _app(), _ctx()
    t = a.tenants.get_tenant(ctx.tenant_id)
    _, plan = a.entitlements.tenant_plan(ctx.tenant_id)
    return {"tenant": t["name"], "plan": plan["name"], "features": plan["features"]}


@mcp.tool()
@_wrap
def kbz_billing_usage() -> dict:
    """Plan limits and month-to-date usage for the tenant."""
    return _app().entitlements.usage_summary(_ctx().tenant_id)


# ------------------------------------------------------------------ retail
@mcp.tool()
@_wrap
def kbz_list_products(limit: int = 50) -> list[dict]:
    """Retail products with SKU, price and stock on hand."""
    ctx = _ctx()
    rows = _app().retail.list_products(ctx, limit=limit)
    return [{"id": r["id"], "sku": r["sku"], "name": r["name"],
             "price_kes": fmt_kes(r["sale_price_cents"]), "stock": r["stock_qty"]} for r in rows]


@mcp.tool()
@_wrap
def kbz_add_product(sku: str, name: str, price_kes: str, cost_kes: str = "0",
                    reorder_level: int = 0) -> dict:
    """Create a retail product. Prices as '1234.56'."""
    p = _app().retail.create_product(_ctx(), sku, name, parse_amount(price_kes),
                                     parse_amount(cost_kes), reorder_level=reorder_level)
    return {"id": p["id"], "sku": p["sku"], "price": fmt_kes(p["sale_price_cents"])}


@mcp.tool()
@_wrap
def kbz_receive_stock(product_id: str, qty: int, ref: str = "") -> dict:
    """Receive +qty units of a product into stock."""
    return _app().retail.adjust_stock(_ctx(), product_id, int(qty), "receive", ref or None)


@mcp.tool()
@_wrap
def kbz_create_sale(items_json: str, payment_method: str = "CASH", mpesa_ref: str = "") -> dict:
    """POS sale. items_json: JSON array like [{"product_id":"...","qty":2}]. Deducts stock."""
    import json as _json
    items = _json.loads(items_json)
    return _app().retail.create_sale(_ctx(), items, payment_method, mpesa_ref or None)


@mcp.tool()
@_wrap
def kbz_low_stock() -> list[dict]:
    """Products at/below reorder level."""
    return _app().retail.low_stock(_ctx())


# ------------------------------------------------------------------ invoicing
@mcp.tool()
@_wrap
def kbz_list_invoices(status: str = "") -> list[dict]:
    """Invoices with number, status and totals."""
    rows = _app().invoicing.list_invoices(_ctx(), status or None)
    return [{"id": r["id"], "number": r["number"], "status": r["status"],
             "gross": fmt_kes(r["gross_cents"]), "paid": fmt_kes(r["paid_cents"])} for r in rows]


@mcp.tool()
@_wrap
def kbz_create_invoice(lines_json: str, customer_id: str = "", due_date: str = "") -> dict:
    """Issue VAT invoice. lines_json: [{"description":"...","qty":1,"unit_price":"1500.00"}]."""
    import json as _json
    lines = _json.loads(lines_json)
    inv = _app().invoicing.create_invoice(_ctx(), lines, customer_id or None, due_date or None)
    return {"id": inv["id"], "number": inv["number"], "gross": inv["gross_fmt"],
            "vat": fmt_kes(inv["vat_cents"])}


@mcp.tool()
@_wrap
def kbz_record_payment(invoice_id: str, amount_kes: str, reference: str = "STK-PUSH") -> dict:
    """Record an incoming payment (M-Pesa reference recommended)."""
    inv = _app().invoicing.record_payment(_ctx(), invoice_id, parse_amount(amount_kes),
                                          "MPESA", reference)
    return {"number": inv["number"], "status": inv["status"],
            "balance": fmt_kes(inv["balance_cents"])}


@mcp.tool()
@_wrap
def kbz_invoice_aging() -> dict:
    """Receivables aging buckets."""
    return _app().invoicing.aging_report(_ctx())


# ------------------------------------------------------------------ restaurant
@mcp.tool()
@_wrap
def kbz_restaurant_menu() -> list[dict]:
    ctx = _ctx()
    return [{"id": m["id"], "name": m["name"], "price": fmt_kes(m["price_cents"])}
            for m in _app().restaurant.list_menu(ctx)]


@mcp.tool()
@_wrap
def kbz_open_order(table_label: str = "") -> dict:
    a, ctx = _app(), _ctx()
    table_id = None
    if table_label:
        match = [t for t in a.restaurant.list_tables(ctx) if t["label"] == table_label.upper()]
        if not match:
            return {"error": {"code": "not_found", "message": f"table {table_label} not found"}}
        table_id = match[0]["id"]
    o = a.restaurant.open_order(ctx, table_id)
    return {"order_id": o["id"], "ticket": o["ticket_no"]}


@mcp.tool()
@_wrap
def kbz_add_order_item(order_id: str, menu_item_id: str, qty: int = 1, notes: str = "") -> dict:
    o = _app().restaurant.add_order_item(_ctx(), order_id, menu_item_id, qty, notes or None)
    return {"ticket": o["ticket_no"], "items": len(o["items"]), "grand_total": o["grand_total_fmt"]}


@mcp.tool()
@_wrap
def kbz_close_order(order_id: str, payment_method: str = "MPESA") -> dict:
    o = _app().restaurant.close_order(_ctx(), order_id, payment_method)
    return {"ticket": o["ticket_no"], "status": o["status"], "grand_total": o["grand_total_fmt"]}


# ------------------------------------------------------------------ hotel
@mcp.tool()
@_wrap
def kbz_hotel_availability(check_in: str, check_out: str) -> list[dict]:
    """Free rooms for [check_in, check_out) dates YYYY-MM-DD."""
    return _app().hotel.availability(_ctx(), check_in, check_out)


@mcp.tool()
@_wrap
def kbz_create_booking(guest_name: str, room_number: str, check_in: str, check_out: str,
                       guest_phone: str = "") -> dict:
    a, ctx = _app(), _ctx()
    match = [r for r in a.hotel.list_rooms(ctx) if r["number"] == room_number.upper()]
    if not match:
        return {"error": {"code": "not_found", "message": f"room {room_number} not found"}}
    b = a.hotel.create_booking(ctx, guest_name, match[0]["id"], check_in, check_out, guest_phone or None)
    return {"booking_id": b["id"], "nights": b["nights"], "total": b["total_fmt"]}


@mcp.tool()
@_wrap
def kbz_check_in(booking_id: str) -> dict:
    b = _app().hotel.check_in(_ctx(), booking_id)
    return {"guest": b["guest_name"], "status": b["status"]}


@mcp.tool()
@_wrap
def kbz_check_out(booking_id: str) -> dict:
    b = _app().hotel.check_out(_ctx(), booking_id)
    return {"guest": b["guest_name"], "status": b["status"]}


# ------------------------------------------------------------------ property
@mcp.tool()
@_wrap
def kbz_property_overview() -> list[dict]:
    props = _app().property.list_properties(_ctx())
    return [{"name": p["name"], "units": [{"id": u["id"], "label": u["label"], "status": u["status"],
             "rent": fmt_kes(u["rent_cents"])} for u in p["units"]]} for p in props]


@mcp.tool()
@_wrap
def kbz_issue_rent_bill(lease_id: str, period: str = "") -> dict:
    b = _app().property.issue_rent_bill(_ctx(), lease_id, period or None)
    return {"bill_id": b["id"], "period": b["period"], "amount": fmt_kes(b["amount_cents"]),
            "due": b["due_date"]}


@mcp.tool()
@_wrap
def kbz_rent_arrears() -> dict:
    return _app().property.arrears_report(_ctx())


# ------------------------------------------------------------------ manufacturing
@mcp.tool()
@_wrap
def kbz_list_boms() -> list[dict]:
    return [{"id": b["id"], "product": b["product_sku"], "version": b["version"]}
            for b in _app().manufacturing.list_boms(_ctx())]


@mcp.tool()
@_wrap
def kbz_material_requirements(bom_id: str, qty: float) -> list[dict]:
    """Explode BOM for `qty` finished units; shows shortfall vs stock."""
    return _app().manufacturing.explode(_ctx(), bom_id, qty)


@mcp.tool()
@_wrap
def kbz_create_work_order(bom_id: str, qty_planned: float) -> dict:
    w = _app().manufacturing.create_work_order(_ctx(), bom_id, qty_planned)
    return {"wo_id": w["id"], "wo_no": w["wo_no"], "status": w["status"]}


@mcp.tool()
@_wrap
def kbz_start_work_order(wo_id: str) -> dict:
    w = _app().manufacturing.start_work_order(_ctx(), wo_id)
    return {"wo_no": w["wo_no"], "status": w["status"]}


@mcp.tool()
@_wrap
def kbz_complete_production(wo_id: str, qty_produced: float) -> dict:
    w = _app().manufacturing.complete_production(_ctx(), wo_id, qty_produced)
    return {"wo_no": w["wo_no"], "produced": w["qty_produced"],
            "material_cost": fmt_kes(w["total_material_cost_cents"])}


# ------------------------------------------------------------------ resources
@mcp.resource("kbz://plans")
def plans_resource() -> str:
    """Pricing catalog as markdown."""
    from ..billing.entitlements import PLANS
    lines = ["| plan | KES/month | features |", "|---|---|---|"]
    for pid, p in PLANS.items():
        lines.append(f"| {p['name']} | {p['price_cents'] // 100:,} | {', '.join(p['features'])} |")
    return "\n".join(lines)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
