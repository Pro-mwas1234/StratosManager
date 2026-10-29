"""Retail: products, stock ledger (shared with restaurant/manufacturing), POS sales."""
from __future__ import annotations

from ..core.db import Database, new_id, now_iso
from ..core.errors import ConflictError, ValidationError
from ..core.money import fmt_kes, parse_amount
from ..billing.entitlements import EntitlementService
from ..core.domain import AuthContext

MODULE = "retail"


class RetailService:
    def __init__(self, db: Database, ent: EntitlementService):
        self.db = db
        self.ent = ent

    def _guard(self, ctx: AuthContext, write: bool = True) -> None:
        self.ent.require_feature(ctx.tenant_id, MODULE)

    # -- products ---------------------------------------------------------------
    def create_product(self, ctx: AuthContext, sku: str, name: str, sale_price, cost_price=0,
                       category: str | None = None, vat_exempt: bool = False,
                       reorder_level: int = 0) -> dict:
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "products")
        if not sku or not name:
            raise ValidationError("sku and name required")
        pid = self.db.tenant_insert("products", ctx.tenant_id, {
            "sku": sku.strip().upper(), "name": name.strip(), "category": category,
            "sale_price_cents": parse_amount(sale_price), "cost_price_cents": parse_amount(cost_price),
            "vat_exempt": vat_exempt, "reorder_level": reorder_level})
        return self.db.tenant_get("products", ctx.tenant_id, pid)

    def list_products(self, ctx: AuthContext, limit: int = 200) -> list[dict]:
        self._guard(ctx, write=False)
        rows = self.db.tenant_rows("products", ctx.tenant_id, where="active=1", limit=limit, order="sku ASC")
        for r in rows:
            r["stock_qty"] = self.stock_level(ctx, r["id"])
        return rows

    def get_product(self, ctx: AuthContext, product_id: str) -> dict:
        p = self.db.tenant_get("products", ctx.tenant_id, product_id)
        p["stock_qty"] = self.stock_level(ctx, product_id)
        return p

    # -- stock ledger -------------------------------------------------------------
    def adjust_stock(self, ctx: AuthContext, product_id: str, delta: int, reason: str = "adjustment",
                     ref: str | None = None) -> dict:
        """Receive (+) or issue (-) stock. Never allows negative on hand."""
        self._guard(ctx)
        self.db.tenant_get("products", ctx.tenant_id, product_id)
        delta = int(delta)
        if delta == 0:
            raise ValidationError("delta must be non-zero")
        on_hand = self.stock_level(ctx, product_id)
        if delta < 0 and on_hand + delta < 0:
            raise ConflictError(f"insufficient stock: on hand {on_hand}, requested {abs(delta)}")
        mid = self.db.tenant_insert("stock_movements", ctx.tenant_id, {
            "product_id": product_id, "delta": delta, "reason": reason, "ref": ref})
        return {"movement_id": mid, "product_id": product_id, "delta": delta,
                "on_hand": self.stock_level(ctx, product_id)}

    def stock_level(self, ctx_or_tenant, product_id: str) -> int:
        tenant_id = getattr(ctx_or_tenant, "tenant_id", ctx_or_tenant)
        r = self.db.one(
            "SELECT COALESCE(SUM(delta),0) q FROM stock_movements WHERE tenant_id=? AND product_id=?",
            (tenant_id, product_id))
        return int(r["q"]) if r else 0

    def low_stock(self, ctx: AuthContext) -> list[dict]:
        out = []
        for p in self.db.tenant_rows("products", ctx.tenant_id, where="active=1 AND reorder_level>0"):
            qty = self.stock_level(ctx, p["id"])
            if qty <= p["reorder_level"]:
                out.append({"sku": p["sku"], "name": p["name"], "on_hand": qty,
                            "reorder_level": p["reorder_level"]})
        return out

    # -- POS sales -----------------------------------------------------------------
    def create_sale(self, ctx: AuthContext, items: list[dict], payment_method: str = "CASH",
                    mpesa_ref: str | None = None, cashier: str | None = None) -> dict:
        """items: [{product_id, qty}] — deducts stock atomically-ish, computes totals."""
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "documents_per_month")
        if not items:
            raise ValidationError("sale needs at least one item")
        lines = []
        total = 0
        for it in items:
            pid = it.get("product_id")
            qty = int(it.get("qty", 1))
            if qty <= 0:
                raise ValidationError("qty must be positive")
            p = self.db.tenant_get("products", ctx.tenant_id, pid)
            on_hand = self.stock_level(ctx, pid)
            if on_hand < qty:
                raise ConflictError(f"'{p['name']}': only {on_hand} in stock, sold {qty}")
            line_total = p["sale_price_cents"] * qty
            total += line_total
            lines.append((p, qty, line_total))
        ts = now_iso()
        receipt = "RCP-" + ts[:10].replace("-", "") + "-" + new_id("")[:6].upper()
        sid = self.db.tenant_insert("sales", ctx.tenant_id, {
            "receipt_no": receipt, "total_cents": total, "payment_method": payment_method.upper(),
            "mpesa_ref": mpesa_ref, "cashier": cashier or ctx.email})
        for p, qty, line_total in lines:
            self.db.tenant_insert("sale_items", ctx.tenant_id, {
                "sale_id": sid, "product_id": p["id"], "qty": qty,
                "unit_price_cents": p["sale_price_cents"], "line_total_cents": line_total})
            self.adjust_stock(ctx, p["id"], -qty, reason="sale", ref=receipt)
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=receipt)
        return {"id": sid, "receipt_no": receipt, "total_cents": total, "total_fmt": fmt_kes(total),
                "payment_method": payment_method.upper(), "items": len(lines), "created_at": ts}

    def list_sales(self, ctx: AuthContext, limit: int = 50) -> list[dict]:
        self._guard(ctx, write=False)
        return self.db.tenant_rows("sales", ctx.tenant_id, limit=limit)

    def daily_summary(self, ctx: AuthContext) -> dict:
        today = now_iso()[:10]
        rows = self.db.query(
            "SELECT COALESCE(SUM(total_cents),0) t, COUNT(*) c FROM sales "
            "WHERE tenant_id=? AND substr(created_at,1,10)=?", (ctx.tenant_id, today))
        r = rows[0]
        return {"date": today, "sales_count": r["c"], "total_cents": r["t"], "total_fmt": fmt_kes(r["t"])}
