"""SaaS plans, entitlement checks, and usage metering.

- Features gate whole modules (retail/hotel/invoicing/restaurant/property/manufacturing) plus
  surfaces ('api', 'mcp').
- Limits are calendar-month counters backed by usage_events; breaching one raises
  PaymentRequiredError which maps to HTTP 402.
"""
from __future__ import annotations

import json

from ..core.db import Database, month_key, new_id, now_iso
from ..core.errors import ForbiddenError, PaymentRequiredError, ValidationError

ALL_FEATURES = ["retail", "hotel", "invoicing", "restaurant", "property", "manufacturing", "api", "mcp"]

PLANS: dict[str, dict] = {
    "starter": {
        "name": "Starter",
        "price_cents": 99_900,  # KES 999/mo
        "features": ["retail", "invoicing", "api"],
        "limits": {"users": 2, "documents_per_month": 500, "products": 200},
    },
    "growth": {
        "name": "Growth",
        "price_cents": 299_900,
        "features": ["retail", "invoicing", "restaurant", "property", "api"],
        "limits": {"users": 10, "documents_per_month": 2000, "products": 2000},
    },
    "pro": {
        "name": "Pro",
        "price_cents": 799_900,
        "features": ALL_FEATURES,
        "limits": {"users": 50, "documents_per_month": 10**9, "products": 10**6},
    },
}


def get_plan(plan_id: str) -> dict:
    plan = PLANS.get(plan_id)
    if not plan:
        raise ValidationError(f"unknown plan '{plan_id}'")
    return plan


class EntitlementService:
    def __init__(self, db: Database):
        self.db = db

    def tenant_plan(self, tenant_id: str) -> tuple[dict, dict]:
        t = self.db.one("SELECT * FROM tenants WHERE id=?", (tenant_id,))
        if not t:
            from ..core.errors import NotFoundError
            raise NotFoundError("tenant not found")
        return t, get_plan(t["plan_id"])

    # -- feature gates ------------------------------------------------------
    def require_feature(self, tenant_id: str, feature: str) -> None:
        _, plan = self.tenant_plan(tenant_id)
        if feature not in plan["features"]:
            raise ForbiddenError(
                f"module '{feature}' not included in your plan; upgrade required",
                feature=feature, plan=plan["name"])

    # -- limit checks + metering -------------------------------------------
    def used(self, tenant_id: str, metric: str) -> int:
        if metric == "users":
            r = self.db.one("SELECT COUNT(*) c FROM users WHERE tenant_id=?", (tenant_id,))
            return r["c"] if r else 0
        if metric == "products":
            r = self.db.one("SELECT COUNT(*) c FROM products WHERE tenant_id=? AND active=1", (tenant_id,))
            return r["c"] if r else 0
        mk = month_key()
        r = self.db.one(
            "SELECT COALESCE(SUM(qty),0) c FROM usage_events WHERE tenant_id=? AND metric=? AND month_key=?",
            (tenant_id, metric, mk))
        return r["c"] if r else 0

    def check_limit(self, tenant_id: str, metric: str, add: int = 1) -> None:
        _, plan = self.tenant_plan(tenant_id)
        limit = plan["limits"].get(metric)
        if limit is None:
            return
        current = self.used(tenant_id, metric)
        if current + add > limit:
            raise PaymentRequiredError(
                f"monthly limit reached for '{metric}' ({current}/{limit}); upgrade your plan",
                metric=metric, limit=limit, used=current, reset=month_key()[:7] + "-01 next month")

    def meter(self, tenant_id: str, metric: str, qty: int = 1, ref: str | None = None) -> None:
        self.db.exec(
            "INSERT INTO usage_events(id,tenant_id,metric,qty,month_key,ref,created_at) VALUES(?,?,?,?,?,?,?)",
            (new_id("usg"), tenant_id, metric, qty, month_key(), ref, now_iso()))

    def usage_summary(self, tenant_id: str) -> dict:
        t, plan = self.tenant_plan(tenant_id)
        metrics = sorted(set(list(plan["limits"].keys()) + ["documents_per_month"]))
        out = {"tenant": t["name"], "plan": plan["name"], "price_kes_cents": plan["price_cents"],
               "month": month_key(), "usage": {}}
        for m in metrics:
            out["usage"][m] = {"used": self.used(tenant_id, m), "limit": plan["limits"].get(m)}
        return out

    # -- subscriptions ------------------------------------------------------
    def subscribe(self, tenant_id: str, plan_id: str) -> dict:
        get_plan(plan_id)  # validates
        self.db.exec("UPDATE tenants SET plan_id=? WHERE id=?", (plan_id, tenant_id))
        from datetime import datetime, timedelta, timezone
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=30)
        sid = new_id("sub")
        self.db.exec(
            "INSERT INTO subscriptions(id,tenant_id,plan_id,status,period_start,period_end,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (sid, tenant_id, plan_id, "active",
             start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ"), now_iso(), now_iso()))
        return self.db.one("SELECT * FROM subscriptions WHERE id=?", (sid,))
