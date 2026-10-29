"""Restaurant: menu, tables, orders with 10% service charge; consumption draws stock if linked."""
from __future__ import annotations

from ..core.db import Database, new_id, now_iso
from ..core.errors import ConflictError, ValidationError
from ..core.money import fmt_kes, parse_amount
from ..billing.entitlements import EntitlementService
from ..core.domain import AuthContext
from .retail import RetailService

MODULE = "restaurant"
SERVICE_CHARGE = 0.10


class RestaurantService:
    def __init__(self, db: Database, ent: EntitlementService, retail: RetailService):
        self.db = db
        self.ent = ent
        self.retail = retail

    def _guard(self, ctx: AuthContext, write: bool = True) -> None:
        self.ent.require_feature(ctx.tenant_id, MODULE)

    # -- menu ---------------------------------------------------------------
    def add_menu_item(self, ctx: AuthContext, name: str, price, category: str | None = None,
                      product_id: str | None = None) -> dict:
        self._guard(ctx)
        if not name.strip():
            raise ValidationError("menu item name required")
        if product_id:
            self.db.tenant_get("products", ctx.tenant_id, product_id)
        mid = self.db.tenant_insert("menu_items", ctx.tenant_id, {
            "name": name.strip(), "category": category, "price_cents": parse_amount(price),
            "product_id": product_id})
        return self.db.tenant_get("menu_items", ctx.tenant_id, mid)

    def list_menu(self, ctx: AuthContext, limit: int = 200) -> list[dict]:
        self._guard(ctx, write=False)
        return self.db.tenant_rows("menu_items", ctx.tenant_id, where="available=1",
                                   order="category ASC, name ASC", limit=limit)

    # -- tables ---------------------------------------------------------------
    def add_table(self, ctx: AuthContext, label: str, seats: int = 4) -> dict:
        self._guard(ctx)
        tid = self.db.tenant_insert("tables", ctx.tenant_id, {"label": label.strip().upper(), "seats": int(seats)})
        return self.db.tenant_get("tables", ctx.tenant_id, tid)

    def list_tables(self, ctx: AuthContext) -> list[dict]:
        self._guard(ctx, write=False)
        return self.db.tenant_rows("tables", ctx.tenant_id, order="label ASC")

    def set_table_status(self, ctx: AuthContext, table_id: str, status: str) -> dict:
        if status not in ("free", "occupied", "reserved", "dirty"):
            raise ValidationError("status must be free|occupied|reserved|dirty")
        self.db.tenant_get("tables", ctx.tenant_id, table_id)
        return self.db.tenant_update("tables", ctx.tenant_id, table_id, {"status": status})

    # -- orders ----------------------------------------------------------------
    def open_order(self, ctx: AuthContext, table_id: str | None = None) -> dict:
        self._guard(ctx)
        if table_id:
            self.db.tenant_get("tables", ctx.tenant_id, table_id)
            self.db.tenant_update("tables", ctx.tenant_id, table_id, {"status": "occupied"})
        ts = now_iso()
        ticket = "TKT-" + ts[:10].replace("-", "") + "-" + new_id("")[:5].upper()
        oid = self.db.tenant_insert("orders", ctx.tenant_id, {
            "ticket_no": ticket, "table_id": table_id, "status": "open"})
        return self.get_order(ctx, oid)

    def add_order_item(self, ctx: AuthContext, order_id: str, menu_item_id: str, qty: int = 1,
                       notes: str | None = None) -> dict:
        self._guard(ctx)
        order = self.db.tenant_get("orders", ctx.tenant_id, order_id)
        if order["status"] != "open":
            raise ConflictError(f"order {order['ticket_no']} is {order['status']}")
        mi = self.db.tenant_get("menu_items", ctx.tenant_id, menu_item_id)
        qty = int(qty)
        if qty <= 0:
            raise ValidationError("qty must be positive")
        # If the dish maps to a tracked product, consume stock (1 movement per unit sold).
        if mi.get("product_id"):
            self.retail.adjust_stock(ctx, mi["product_id"], -qty, reason="kitchen", ref=order["ticket_no"])
        line_total = mi["price_cents"] * qty
        self.db.tenant_insert("order_items", ctx.tenant_id, {
            "order_id": order_id, "menu_item_id": menu_item_id, "qty": qty,
            "unit_price_cents": mi["price_cents"], "line_total_cents": line_total, "notes": notes})
        return self._recalc(ctx, order_id)

    def _recalc(self, ctx: AuthContext, order_id: str) -> dict:
        items = self.db.tenant_rows("order_items", ctx.tenant_id, where="order_id=?", params=(order_id,))
        subtotal = sum(i["line_total_cents"] for i in items)
        svc = round(subtotal * SERVICE_CHARGE)
        self.db.tenant_update("orders", ctx.tenant_id, order_id,
                              {"total_cents": subtotal, "service_charge_cents": svc})
        o = self.get_order(ctx, order_id)
        return o

    def get_order(self, ctx: AuthContext, order_id: str) -> dict:
        o = self.db.tenant_get("orders", ctx.tenant_id, order_id)
        o["items"] = self.db.tenant_rows("order_items", ctx.tenant_id,
                                         where="order_id=?", params=(order_id,), order="created_at ASC")
        o["grand_total_cents"] = o["total_cents"] + o["service_charge_cents"]
        o["grand_total_fmt"] = fmt_kes(o["grand_total_cents"])
        return o

    def close_order(self, ctx: AuthContext, order_id: str, payment_method: str = "MPESA") -> dict:
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "documents_per_month")
        o = self.db.tenant_get("orders", ctx.tenant_id, order_id)
        if o["status"] != "open":
            raise ConflictError(f"order already {o['status']}")
        o = self._recalc(ctx, order_id)
        self.db.tenant_update("orders", ctx.tenant_id, order_id, {"status": "closed"})
        if o.get("table_id"):
            self.db.tenant_update("tables", ctx.tenant_id, o["table_id"], {"status": "dirty"})
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=o["ticket_no"])
        o["payment_method"] = payment_method.upper()
        return o

    def kitchen_ticket(self, ctx: AuthContext, order_id: str) -> str:
        """Plain-text ticket for the kitchen printer."""
        o = self.get_order(ctx, order_id)
        lines = [f"** KITCHEN {o['ticket_no']} **", f"table: {o.get('table_id') or 'takeaway'}"]
        for it in o["items"]:
            mi = self.db.tenant_get("menu_items", ctx.tenant_id, it["menu_item_id"])
            note = f" ({it['notes']})" if it.get("notes") else ""
            lines.append(f"{it['qty']}x {mi['name']}{note}")
        return "\n".join(lines)

    def list_orders(self, ctx: AuthContext, status: str | None = None, limit: int = 50) -> list[dict]:
        self._guard(ctx, write=False)
        where, params = "", ()
        if status:
            where, params = "status=?", (status,)
        return self.db.tenant_rows("orders", ctx.tenant_id, where=where, params=params, limit=limit)
