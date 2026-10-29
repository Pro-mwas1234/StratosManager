"""Manufacturing: BOMs, work orders, production runs.

Stock effects reuse the retail ledger (products + stock_movements):
- start_work_order  -> issues components (-qty * planned)
- complete_run      -> consumes remaining components for actual qty, receives finished goods (+qty)
"""
from __future__ import annotations

from ..core.db import Database, new_id, now_iso
from ..core.errors import ConflictError, ValidationError
from ..core.money import parse_amount
from ..billing.entitlements import EntitlementService
from ..core.domain import AuthContext
from .retail import RetailService

MODULE = "manufacturing"


class ManufacturingService:
    def __init__(self, db: Database, ent: EntitlementService, retail: RetailService):
        self.db = db
        self.ent = ent
        self.retail = retail

    def _guard(self, ctx: AuthContext, write: bool = True) -> None:
        self.ent.require_feature(ctx.tenant_id, MODULE)

    # -- BOM ---------------------------------------------------------------
    def create_bom(self, ctx: AuthContext, product_id: str, components: list[dict],
                   version: str = "v1") -> dict:
        """components: [{product_id, qty}]"""
        self._guard(ctx)
        parent = self.db.tenant_get("products", ctx.tenant_id, product_id)
        if not components:
            raise ValidationError("BOM needs at least one component")
        seen = set()
        for c in components:
            comp = self.db.tenant_get("products", ctx.tenant_id, c["product_id"])
            if c["product_id"] == product_id:
                raise ValidationError("component cannot be the finished product itself")
            if float(c.get("qty", 0)) <= 0:
                raise ValidationError(f"component '{comp['sku']}' qty must be positive")
            if c["product_id"] in seen:
                raise ValidationError(f"duplicate component {comp['sku']}")
            seen.add(c["product_id"])
        bid = self.db.tenant_insert("boms", ctx.tenant_id, {"product_id": product_id, "version": version})
        for c in components:
            self.db.tenant_insert("bom_components", ctx.tenant_id, {
                "bom_id": bid, "component_product_id": c["product_id"], "qty": float(c.get("qty", 1))})
        return self.get_bom(ctx, bid)

    def get_bom(self, ctx: AuthContext, bom_id: str) -> dict:
        b = self.db.tenant_get("boms", ctx.tenant_id, bom_id)
        comps = []
        for c in self.db.tenant_rows("bom_components", ctx.tenant_id, where="bom_id=?", params=(bom_id,)):
            p = self.db.tenant_get("products", ctx.tenant_id, c["component_product_id"])
            comps.append({"product_id": p["id"], "sku": p["sku"], "name": p["name"],
                          "qty_per_unit": c["qty"], "on_hand": self.retail.stock_level(ctx, p["id"])})
        b["components"] = comps
        return b

    def list_boms(self, ctx: AuthContext) -> list[dict]:
        self._guard(ctx, write=False)
        out = []
        for b in self.db.tenant_rows("boms", ctx.tenant_id):
            p = self.db.tenant_get("products", ctx.tenant_id, b["product_id"])
            b["product_sku"], b["product_name"] = p["sku"], p["name"]
            out.append(b)
        return out

    # -- material requirement planning ------------------------------------------
    def explode(self, ctx: AuthContext, bom_id: str, qty: float) -> list[dict]:
        """Requirement per component for producing `qty` units."""
        bom = self.get_bom(ctx, bom_id)
        req = []
        for c in bom["components"]:
            need = round(c["qty_per_unit"] * qty, 3)
            req.append({"sku": c["sku"], "name": c["name"], "required": need,
                        "on_hand": c["on_hand"], "shortfall": max(0, need - c["on_hand"])})
        return req

    # -- work orders -----------------------------------------------------------
    def create_work_order(self, ctx: AuthContext, bom_id: str, qty_planned: float,
                          notes: str | None = None) -> dict:
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "documents_per_month")
        bom = self.db.tenant_get("boms", ctx.tenant_id, bom_id)
        if qty_planned <= 0:
            raise ValidationError("qty_planned must be positive")
        wo_no = "WO-" + now_iso()[:10].replace("-", "") + "-" + new_id("")[:5].upper()
        wid = self.db.tenant_insert("work_orders", ctx.tenant_id, {
            "wo_no": wo_no, "bom_id": bom_id, "qty_planned": float(qty_planned), "notes": notes})
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=wo_no)
        return self.get_work_order(ctx, wid)

    def get_work_order(self, ctx: AuthContext, wo_id: str) -> dict:
        w = self.db.tenant_get("work_orders", ctx.tenant_id, wo_id)
        w["requirements"] = self.explode(ctx, w["bom_id"], w["qty_planned"])
        return w

    def list_work_orders(self, ctx: AuthContext, status: str | None = None, limit: int = 100) -> list[dict]:
        self._guard(ctx, write=False)
        where, params = "", ()
        if status:
            where, params = "status=?", (status,)
        return self.db.tenant_rows("work_orders", ctx.tenant_id, where=where, params=params, limit=limit)

    def start_work_order(self, ctx: AuthContext, wo_id: str) -> dict:
        """Issue all materials for the planned quantity; fails fast on any shortfall."""
        w = self.db.tenant_get("work_orders", ctx.tenant_id, wo_id)
        if w["status"] != "planned":
            raise ConflictError(f"work order is {w['status']}")
        for r in self.explode(ctx, w["bom_id"], w["qty_planned"]):
            if r["shortfall"] > 0:
                raise ConflictError(f"material shortage: {r['sku']} needs {r['required']}, have {r['on_hand']}")
        bom = self.db.tenant_get("boms", ctx.tenant_id, w["bom_id"])
        for c in self.db.tenant_rows("bom_components", ctx.tenant_id, where="bom_id=?", params=(bom["id"],)):
            issue_qty = -int(round(c["qty"] * w["qty_planned"]))
            self.retail.adjust_stock(ctx, c["component_product_id"], issue_qty,
                                     reason="production_issue", ref=w["wo_no"])
        return self.db.tenant_update("work_orders", ctx.tenant_id, wo_id, {"status": "in_progress"})

    def complete_production(self, ctx: AuthContext, wo_id: str, qty_produced: float) -> dict:
        """Receive finished goods. Scrap (planned - produced) stays as consumed material cost."""
        w = self.db.tenant_get("work_orders", ctx.tenant_id, wo_id)
        if w["status"] != "in_progress":
            raise ConflictError("start the work order before completing it")
        if qty_produced <= 0 or qty_produced > w["qty_planned"]:
            raise ValidationError(f"qty_produced must be in (0, {w['qty_planned']}]")
        bom = self.db.tenant_get("boms", ctx.tenant_id, w["bom_id"])
        # unit cost from components at cost price
        unit_cost = 0
        for c in self.db.tenant_rows("bom_components", ctx.tenant_id, where="bom_id=?", params=(bom["id"],)):
            comp = self.db.tenant_get("products", ctx.tenant_id, c["component_product_id"])
            unit_cost += round(comp["cost_price_cents"] * c["qty"])
        finished = self.db.tenant_get("products", ctx.tenant_id, bom["product_id"])
        recv = int(round(qty_produced))
        if recv != qty_produced:
            raise ValidationError("fractional finished units not supported in v1")
        self.retail.adjust_stock(ctx, finished["id"], recv, reason="production_receipt", ref=w["wo_no"])
        w = self.db.tenant_update("work_orders", ctx.tenant_id, wo_id, {
            "qty_produced": float(qty_produced), "status": "completed"})
        w["unit_material_cost_cents"] = unit_cost
        w["total_material_cost_cents"] = unit_cost * recv
        return w
