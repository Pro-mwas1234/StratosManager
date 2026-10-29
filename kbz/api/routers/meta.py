from fastapi import APIRouter, Depends, Request

from .deps import get_ctx

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "kabiz-api"}


@router.get("/me")
def me(request: Request, ctx=Depends(get_ctx)):
    kbz = request.app.state.kbz
    tenant = kbz.tenants.get_tenant(ctx.tenant_id)
    _, plan = kbz.entitlements.tenant_plan(ctx.tenant_id)
    return {"user": {"id": ctx.user_id, "email": ctx.email, "role": ctx.role},
            "tenant": {"id": tenant["id"], "name": tenant["name"], "kra_pin": tenant["kra_pin"],
                       "phone": tenant["phone"]},
            "plan": {"id": tenant["plan_id"], "name": plan["name"], "features": plan["features"]}}
