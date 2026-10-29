from fastapi import APIRouter, Depends, Request

from ...core.domain import AuthContext
from ..schemas import (RegisterIn, LoginIn, StaffIn)
from .deps import get_ctx

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterIn, request: Request):
    app = request.app.state.stratos
    user, token = app.users.register_user(body.email, body.password, body.tenant_name,
                                          body.kra_pin, body.phone, body.plan_id)
    if body.plan_id and body.plan_id != "starter":
        app.entitlements.subscribe(user["tenant_id"], body.plan_id)
    return {"user": {k: user[k] for k in ("id", "email", "role", "tenant_id")}, "token": token}


@router.post("/login")
def login(body: LoginIn, request: Request):
    app = request.app.state.stratos
    ctx, token = app.users.login(body.email, body.password, kind="api")
    tenant = app.tenants.get_tenant(ctx.tenant_id)
    _, plan = app.entitlements.tenant_plan(ctx.tenant_id)
    return {"token": token, "user_id": ctx.user_id, "email": ctx.email, "role": ctx.role,
            "tenant_id": ctx.tenant_id, "tenant_name": tenant["name"],
            "plan": tenant["plan_id"], "plan_name": plan["name"], "features": plan["features"]}


@router.post("/logout")
def logout(request: Request, ctx: AuthContext = Depends(get_ctx)):
    app = request.app.state.stratos
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        app.users.revoke_token(header.split(" ", 1)[1].strip())
    return {"ok": True}


@router.get("/session")
def session(request: Request, ctx: AuthContext = Depends(get_ctx)):
    """App resume / token validity check."""
    tenant = request.app.state.stratos.tenants.get_tenant(ctx.tenant_id)
    return {"valid": True, "user_id": ctx.user_id, "email": ctx.email, "role": ctx.role,
            "tenant_id": tenant["id"], "tenant_name": tenant["name"], "plan": tenant["plan_id"]}


@router.post("/staff")
def add_staff(body: StaffIn, request: Request, ctx: AuthContext = Depends(get_ctx)):
    app = request.app.state.stratos
    app.entitlements.check_limit(ctx.tenant_id, "users")
    if not ctx.is_owner:
        from ...core.errors import ForbiddenError
        raise ForbiddenError("only owners can add staff")
    user = app.users.add_user(body.email, body.password, ctx.tenant_id, role="staff")
    app.entitlements.meter(ctx.tenant_id, "documents_per_month", ref=f"USER-{user['id']}")
    return {k: user[k] for k in ("id", "email", "role")}
