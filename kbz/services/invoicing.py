"""Invoicing: customers, VAT invoices with sequential numbers, payments (M-Pesa refs)."""
from __future__ import annotations

from ..core.db import Database, new_id, now_iso
from ..core.errors import ConflictError, ValidationError
from ..core.money import VAT_RATE_DEFAULT, fmt_kes, parse_amount, vat_split
from ..billing.entitlements import EntitlementService
from ..core.domain import AuthContext

MODULE = "invoicing"


class InvoicingService:
    def __init__(self, db: Database, ent: EntitlementService):
        self.db = db
        self.ent = ent

    # -- guards ---------------------------------------------------------------
    def _guard(self, ctx: AuthContext, write: bool = True) -> None:
        self.ent.require_feature(ctx.tenant_id, MODULE)
        if write:
            self.ent.check_limit(ctx.tenant_id, "users")  # cheap structural guard placeholder

    # -- customers ------------------------------------------------------------
    def create_customer(self, ctx: AuthContext, name: str, email: str | None = None,
                        phone: str | None = None, kra_pin: str | None = None,
                        address: str | None = None) -> dict:
        self._guard(ctx)
        from ..core.domain import validate_kra_pin, normalize_phone
        if not name or not name.strip():
            raise ValidationError("customer name required")
        cid = self.db.tenant_insert("customers", ctx.tenant_id, {
            "name": name.strip(), "email": email, "phone": normalize_phone(phone),
            "kra_pin": validate_kra_pin(kra_pin), "address": address})
        return self.db.tenant_get("customers", ctx.tenant_id, cid)

    def list_customers(self, ctx: AuthContext, limit: int = 100) -> list[dict]:
        self._guard(ctx, write=False)
        return self.db.tenant_rows("customers", ctx.tenant_id, limit=limit)

    # -- invoice numbering ------------------------------------------------------
    def next_number(self, ctx: AuthContext) -> str:
        year = now_iso()[:4]
        rows = self.db.tenant_rows("invoices", ctx.tenant_id,
                                   where="number LIKE ?", params=(f"INV-{year}-%",),
                                   order="number DESC", limit=1)
        seq = 1
        if rows:
            try:
                seq = int(rows[0]["number"].rsplit("-", 1)[1]) + 1
            except ValueError:
                pass
        return f"INV-{year}-{seq:05d}"

    # -- invoices ---------------------------------------------------------------
    def create_invoice(self, ctx: AuthContext, lines: list[dict], customer_id: str | None = None,
                       due_date: str | None = None, notes: str | None = None,
                       inclusive_vat: bool = False) -> dict:
        """lines: [{description, qty?, unit_price (str|int cents), vat_rate?}]"""
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "documents_per_month")
        if customer_id:
            self.db.tenant_get("customers", ctx.tenant_id, customer_id)
        if not lines:
            raise ValidationError("invoice needs at least one line")
        net_total = vat_total = 0
        parsed_lines = []
        for ln in lines:
            desc = (ln.get("description") or "").strip()
            if not desc:
                raise ValidationError("line description required")
            qty = float(ln.get("qty", 1))
            if qty <= 0:
                raise ValidationError("line qty must be positive")
            unit = int(ln["unit_price_cents"]) if "unit_price_cents" in ln else parse_amount(ln.get("unit_price"))
            rate = float(ln.get("vat_rate", VAT_RATE_DEFAULT))
            line_net = round(unit * qty)
            if inclusive_vat:
                n, v, _ = vat_split(line_net, rate, inclusive=True)
            else:
                n, v, _ = vat_split(line_net, rate)
            net_total += n
            vat_total += v
            parsed_lines.append((desc, qty, unit, rate, n, v))
        number = self.next_number(ctx)
        gross = net_total + vat_total
        iid = self.db.tenant_insert("invoices", ctx.tenant_id, {
            "number": number, "customer_id": customer_id, "status": "issued",
            "issue_date": now_iso()[:10], "due_date": due_date,
            "net_cents": net_total, "vat_cents": vat_total, "gross_cents": gross, "notes": notes})
        for desc, qty, unit, rate, n, v in parsed_lines:
            self.db.tenant_insert("invoice_lines", ctx.tenant_id, {
                "invoice_id": iid, "description": desc, "qty": qty, "unit_price_cents": unit,
                "vat_rate": rate, "line_net_cents": n, "line_vat_cents": v})
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=number)
        return self.get_invoice(ctx, iid)

    def get_invoice(self, ctx: AuthContext, invoice_id: str) -> dict:
        inv = self.db.tenant_get("invoices", ctx.tenant_id, invoice_id)
        inv["lines"] = self.db.tenant_rows("invoice_lines", ctx.tenant_id,
                                           where="invoice_id=?", params=(invoice_id,), order="created_at ASC")
        inv["payments"] = self.db.tenant_rows("payments", ctx.tenant_id,
                                              where="invoice_id=?", params=(invoice_id,), order="created_at ASC")
        inv["balance_cents"] = inv["gross_cents"] - inv["paid_cents"]
        inv["gross_fmt"] = fmt_kes(inv["gross_cents"])
        return inv

    # app-facing alias → storage statuses ('issued' is what an open invoice is called server-side)
    STATUS_ALIASES = {"open": ("issued", "partially_paid")}

    def list_invoices(self, ctx: AuthContext, status: str | None = None, limit: int = 100) -> list[dict]:
        self._guard(ctx, write=False)
        where, params = "", ()
        if status:
            mapped = self.STATUS_ALIASES.get(status)
            if mapped:
                where = f"status IN ({','.join('?' * len(mapped))})"
                params = tuple(mapped)
            else:
                where, params = "status=?", (status,)
        return self.db.tenant_rows("invoices", ctx.tenant_id, where=where, params=params, limit=limit)

    def record_payment(self, ctx: AuthContext, invoice_id: str, amount, method: str = "MPESA",
                       reference: str | None = None) -> dict:
        self._guard(ctx)
        inv = self.db.tenant_get("invoices", ctx.tenant_id, invoice_id)
        amt = parse_amount(amount)
        if amt <= 0:
            raise ValidationError("payment amount must be positive")
        if inv["status"] == "paid":
            raise ConflictError(f"invoice {inv['number']} already paid")
        balance = inv["gross_cents"] - inv["paid_cents"]
        if amt > balance:
            raise ValidationError(f"payment {fmt_kes(amt)} exceeds balance {fmt_kes(balance)}")
        pid = self.db.tenant_insert("payments", ctx.tenant_id, {
            "invoice_id": invoice_id, "method": method.upper(), "reference": reference,
            "amount_cents": amt, "paid_at": now_iso()})
        paid = inv["paid_cents"] + amt
        status = "paid" if paid >= inv["gross_cents"] else "partially_paid"
        self.db.tenant_update("invoices", ctx.tenant_id, invoice_id, {"paid_cents": paid, "status": status})
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=f"PAY-{inv['number']}")
        return self.get_invoice(ctx, invoice_id)

    def void_invoice(self, ctx: AuthContext, invoice_id: str) -> dict:
        if not ctx.is_owner:
            from ..core.errors import ForbiddenError
            raise ForbiddenError("only owners can void invoices")
        inv = self.db.tenant_get("invoices", ctx.tenant_id, invoice_id)
        if inv["paid_cents"]:
            raise ConflictError("cannot void a paid invoice")
        return self.db.tenant_update("invoices", ctx.tenant_id, invoice_id, {"status": "void"})

    def aging_report(self, ctx: AuthContext) -> dict:
        """Outstanding invoices bucketed by days past due."""
        self._guard(ctx, write=False)
        today = now_iso()[:10]
        buckets = {"current": 0, "overdue_1_30": 0, "overdue_31_60": 0, "overdue_60_plus": 0}
        count = 0
        for inv in self.db.tenant_rows("invoices", ctx.tenant_id,
                                       where="status IN ('issued','partially_paid')"):
            bal = inv["gross_cents"] - inv["paid_cents"]
            count += 1
            due = inv["due_date"] or inv["issue_date"]
            if not due or due >= today:
                buckets["current"] += bal
                continue
            from datetime import date
            d1 = date.fromisoformat(due)
            d2 = date.fromisoformat(today)
            days = (d2 - d1).days
            if days <= 30:
                buckets["overdue_1_30"] += bal
            elif days <= 60:
                buckets["overdue_31_60"] += bal
            else:
                buckets["overdue_60_plus"] += bal
        return {"as_of": today, "open_invoices": count,
                "buckets_cents": buckets,
                "buckets_kes": {k: fmt_kes(v) for k, v in buckets.items()}}
