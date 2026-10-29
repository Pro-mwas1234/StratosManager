"""Cross-module counters for the mobile Home dashboard (one call per refresh).

Read-only aggregate over module tables; each section is emitted only when the tenant's plan
entitles that feature, mirroring what the app shows on its home cards.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..core.db import Database, now_iso
from ..core.domain import AuthContext
from ..core.money import fmt_kes


class DashboardService:
    def __init__(self, db: Database, entitlements, retail, hotel):
        self.db = db
        self.ent = entitlements
        self.retail = retail
        self.hotel = hotel

    def _count(self, sql: str, params: tuple) -> int:
        rows = self.db.query(sql, params)
        return rows[0]["c"] if rows else 0

    def summary(self, ctx: AuthContext) -> dict:
        tid = ctx.tenant_id
        today = now_iso()[:10]
        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
        tenant_row, plan = self.ent.tenant_plan(tid)
        features = set(plan["features"])

        out: dict = {
            "generated_at": now_iso(),
            "tenant": {"plan_id": tenant_row["plan_id"], "plan_name": plan["name"],
                       "features": sorted(features)},
            "usage": self.ent.usage_summary(tid),
        }

        if "retail" in features:
            r = self.db.query(
                "SELECT COALESCE(SUM(total_cents),0) t, COUNT(*) c FROM sales "
                "WHERE tenant_id=? AND substr(created_at,1,10)=?", (tid, today))[0]
            out["retail"] = {"today_sales_count": r["c"], "today_total_cents": r["t"],
                             "today_total_fmt": fmt_kes(r["t"]),
                             "low_stock_count": len(self.retail.low_stock(ctx))}

        if "invoicing" in features:
            due = self.db.query(
                "SELECT COALESCE(SUM(gross_cents - paid_cents),0) t, COUNT(*) c FROM invoices "
                "WHERE tenant_id=? AND status IN ('issued','partially_paid')", (tid,))[0]
            out["invoicing"] = {"open_invoices": due["c"], "receivable_cents": due["t"],
                                "receivable_fmt": fmt_kes(due["t"])}

        if "restaurant" in features:
            out["restaurant"] = {"open_orders": self._count(
                "SELECT COUNT(*) c FROM orders WHERE tenant_id=? AND status='open'", (tid,))}

        if "hotel" in features:
            occ = self.hotel.occupancy_report(ctx, today)
            out["hotel"] = {
                "arrivals_today": self._count(
                    "SELECT COUNT(*) c FROM bookings WHERE tenant_id=? AND status='reserved' "
                    "AND check_in_date<=? AND check_out_date>?", (tid, tomorrow, today)),
                "departures_today": self._count(
                    "SELECT COUNT(*) c FROM bookings WHERE tenant_id=? AND status='checked_in' "
                    "AND check_out_date<=?", (tid, tomorrow)),
                "in_house": self._count(
                    "SELECT COUNT(*) c FROM bookings WHERE tenant_id=? AND status='checked_in'", (tid,)),
                "occupancy_pct": occ["occupancy_pct"],
            }

        if "property" in features:
            bills = self.db.query(
                "SELECT COALESCE(SUM(amount_cents - paid_cents),0) t, COUNT(*) c FROM rent_bills "
                "WHERE tenant_id=? AND status!='paid' AND amount_cents > paid_cents", (tid,))[0]
            out["property"] = {"unpaid_bills": bills["c"], "arrears_cents": bills["t"],
                               "arrears_fmt": fmt_kes(bills["t"])}

        if "manufacturing" in features:
            out["manufacturing"] = {"work_orders_open": self._count(
                "SELECT COUNT(*) c FROM work_orders WHERE tenant_id=? AND status IN "
                "('planned','in_progress')", (tid,))}

        return out
