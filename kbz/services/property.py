"""Property rental: properties, units, leases, monthly rent bills, payments, arrears."""
from __future__ import annotations

from datetime import date, timedelta

from ..core.db import Database, month_key, new_id, now_iso
from ..core.errors import ConflictError, ValidationError
from ..core.money import fmt_kes, parse_amount
from ..billing.entitlements import EntitlementService
from ..core.domain import AuthContext

MODULE = "property"


class PropertyService:
    def __init__(self, db: Database, ent: EntitlementService):
        self.db = db
        self.ent = ent

    def _guard(self, ctx: AuthContext, write: bool = True) -> None:
        self.ent.require_feature(ctx.tenant_id, MODULE)

    # -- properties & units ----------------------------------------------------
    def add_property(self, ctx: AuthContext, name: str, location: str | None = None) -> dict:
        self._guard(ctx)
        if not name.strip():
            raise ValidationError("property name required")
        pid = self.db.tenant_insert("properties", ctx.tenant_id, {"name": name.strip(), "location": location})
        return self.db.tenant_get("properties", ctx.tenant_id, pid)

    def list_properties(self, ctx: AuthContext) -> list[dict]:
        self._guard(ctx, write=False)
        props = self.db.tenant_rows("properties", ctx.tenant_id, order="name ASC")
        for p in props:
            p["units"] = self.db.tenant_rows("units", ctx.tenant_id, where="property_id=?", params=(p["id"],))
        return props

    def add_unit(self, ctx: AuthContext, property_id: str, label: str, rent) -> dict:
        self._guard(ctx)
        self.db.tenant_get("properties", ctx.tenant_id, property_id)
        uid = self.db.tenant_insert("units", ctx.tenant_id, {
            "property_id": property_id, "label": label.strip().upper(), "rent_cents": parse_amount(rent)})
        return self.db.tenant_get("units", ctx.tenant_id, uid)

    # -- leases ------------------------------------------------------------------
    def create_lease(self, ctx: AuthContext, unit_id: str, tenant_name: str, start_date: str,
                     end_date: str, rent=None, deposit=0, tenant_phone: str | None = None) -> dict:
        self._guard(ctx)
        unit = self.db.tenant_get("units", ctx.tenant_id, unit_id)
        try:
            sd, ed = date.fromisoformat(start_date), date.fromisoformat(end_date)
        except ValueError:
            raise ValidationError("dates must be YYYY-MM-DD")
        if ed <= sd:
            raise ValidationError("end_date must be after start_date")
        active = self.db.tenant_rows("leases", ctx.tenant_id, where="unit_id=? AND status='active'",
                                     params=(unit_id,))
        if active:
            raise ConflictError(f"unit {unit['label']} already has an active lease")
        lid = self.db.tenant_insert("leases", ctx.tenant_id, {
            "unit_id": unit_id, "tenant_name": tenant_name.strip(), "tenant_phone": tenant_phone,
            "start_date": sd.isoformat(), "end_date": ed.isoformat(),
            "rent_cents": parse_amount(rent) if rent is not None else unit["rent_cents"],
            "deposit_cents": parse_amount(deposit), "status": "active"})
        self.db.tenant_update("units", ctx.tenant_id, unit_id, {"status": "occupied"})
        return self.db.tenant_get("leases", ctx.tenant_id, lid)

    def end_lease(self, ctx: AuthContext, lease_id: str) -> dict:
        l = self.db.tenant_get("leases", ctx.tenant_id, lease_id)
        if l["status"] != "active":
            raise ConflictError(f"lease is {l['status']}")
        self.db.tenant_update("leases", ctx.tenant_id, lease_id, {"status": "ended"})
        self.db.tenant_update("units", ctx.tenant_id, l["unit_id"], {"status": "vacant"})
        return self.db.tenant_get("leases", ctx.tenant_id, lease_id)

    def list_leases(self, ctx: AuthContext, status: str | None = "active", limit: int = 100) -> list[dict]:
        self._guard(ctx, write=False)
        where, params = "", ()
        if status:
            where, params = "status=?", (status,)
        return self.db.tenant_rows("leases", ctx.tenant_id, where=where, params=params, limit=limit)

    # -- rent bills ----------------------------------------------------------------
    def issue_rent_bill(self, ctx: AuthContext, lease_id: str, period: str | None = None,
                        due_day: int = 10) -> dict:
        """period = 'YYYY-MM' (defaults to current month). One bill per lease per period."""
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "documents_per_month")
        lease = self.db.tenant_get("leases", ctx.tenant_id, lease_id)
        if lease["status"] != "active":
            raise ConflictError("lease not active")
        period = period or month_key()
        try:
            y, m = map(int, period.split("-"))
            due = date(y, m, min(due_day, 28)).isoformat()
        except ValueError:
            raise ValidationError("period must be YYYY-MM")
        bid = self.db.tenant_insert("rent_bills", ctx.tenant_id, {
            "lease_id": lease_id, "period": period, "due_date": due,
            "amount_cents": lease["rent_cents"]})
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=f"RENT-{period}")
        return self.get_bill(ctx, bid)

    def get_bill(self, ctx: AuthContext, bill_id: str) -> dict:
        b = self.db.tenant_get("rent_bills", ctx.tenant_id, bill_id)
        b["balance_cents"] = b["amount_cents"] - b["paid_cents"]
        b["payments"] = self.db.tenant_rows("rent_payments", ctx.tenant_id,
                                            where="bill_id=?", params=(bill_id,))
        return b

    def record_rent_payment(self, ctx: AuthContext, bill_id: str, amount, method: str = "MPESA",
                            reference: str | None = None) -> dict:
        self._guard(ctx)
        b = self.db.tenant_get("rent_bills", ctx.tenant_id, bill_id)
        amt = parse_amount(amount)
        balance = b["amount_cents"] - b["paid_cents"]
        if amt <= 0:
            raise ValidationError("amount must be positive")
        if amt > balance:
            raise ValidationError(f"payment exceeds balance {fmt_kes(balance)}")
        self.db.tenant_insert("rent_payments", ctx.tenant_id, {
            "bill_id": bill_id, "amount_cents": amt, "method": method.upper(), "reference": reference,
            "paid_at": now_iso()})
        paid = b["paid_cents"] + amt
        status = "paid" if paid >= b["amount_cents"] else "partially_paid"
        self.db.tenant_update("rent_bills", ctx.tenant_id, bill_id, {"paid_cents": paid, "status": status})
        return self.get_bill(ctx, bill_id)

    def arrears_report(self, ctx: AuthContext) -> dict:
        """Unpaid/partially-paid bills with days overdue."""
        self._guard(ctx, write=False)
        today = now_iso()[:10]
        rows = []
        total = 0
        for b in self.db.tenant_rows("rent_bills", ctx.tenant_id,
                                     where="status IN ('pending','partially_paid')"):
            bal = b["amount_cents"] - b["paid_cents"]
            overdue_days = max(0, (date.fromisoformat(today) - date.fromisoformat(b["due_date"])).days)
            if bal > 0:
                total += bal
                lease = self.db.tenant_get("leases", ctx.tenant_id, b["lease_id"])
                rows.append({"bill_id": b["id"], "period": b["period"], "tenant": lease["tenant_name"],
                             "balance_cents": bal, "balance_fmt": fmt_kes(bal),
                             "due_date": b["due_date"], "overdue_days": overdue_days})
        return {"as_of": today, "total_arrears_cents": total, "total_arrears_fmt": fmt_kes(total),
                "bills": rows}
