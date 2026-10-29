from fastapi import APIRouter, Depends, Request

from ..schemas import SubscribeIn
from ...billing.entitlements import PLANS
from .deps import get_ctx

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans")
def plans():
    """Public catalog."""
    return [{"id": pid, "name": p["name"], "price_kes_cents": p["price_cents"],
             "features": p["features"], "limits": p["limits"]} for pid, p in PLANS.items()]


@router.get("/usage")
def usage(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.kbz.entitlements.usage_summary(ctx.tenant_id)


@router.post("/subscribe")
def subscribe(body: SubscribeIn, request: Request, ctx=Depends(get_ctx)):
    if not ctx.is_owner:
        from ...core.errors import ForbiddenError
        raise ForbiddenError("only owners can change subscription")
    return request.app.state.kbz.entitlements.subscribe(ctx.tenant_id, body.plan_id)
