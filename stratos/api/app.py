"""FastAPI app factory: auth dependency, error envelope, module routers, mobile-app support."""
from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..app import App
from ..core.db import new_id, now_iso
from ..core.domain import AuthContext
from ..core.errors import StratosError


def create_app(application: App | None = None) -> FastAPI:
    application = application or App()
    api = FastAPI(title="StratosManager API", version="0.2.0",
                  description="Multi-tenant business platform for Kenyan SMEs (Android app backend)")
    api.state.stratos = application

    # -- CORS: Android app / dev tools ------------------------------------------
    api.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
        expose_headers=["X-Idempotent-Replay"])

    # -- error envelope ----------------------------------------------------------
    @api.exception_handler(StratosError)
    async def stratos_error_handler(request: Request, exc: StratosError):
        return JSONResponse(status_code=exc.http_status, content={
            "error": {"code": exc.code, "message": exc.message, "details": exc.details}})

    # -- idempotency middleware (offline write queue replay safety) --------------
    application.db.exec("""CREATE TABLE IF NOT EXISTS idempotency(
        key TEXT PRIMARY KEY, tenant_id TEXT, route TEXT, status_code INTEGER,
        body TEXT, created_at TEXT)""")

    @api.middleware("http")
    async def idempotency_guard(request: Request, call_next):
        key = request.headers.get("idempotency-key")
        if key and request.method.upper() == "POST" and request.url.path != "/auth/register":
            row = application.db.one("SELECT * FROM idempotency WHERE key=?", (key,))
            if row:  # replay: return stored response verbatim
                return JSONResponse(status_code=row["status_code"],
                                    content=json.loads(row["body"]),
                                    headers={"X-Idempotent-Replay": "true"})
            response = await call_next(request)
            if 200 <= response.status_code < 300:
                payload = b""
                async for chunk in response.body_iterator:
                    payload += chunk if isinstance(chunk, bytes) else chunk.encode()
                tid = getattr(getattr(request.state, "ctx", None), "tenant_id", None)
                application.db.exec(
                    "INSERT OR REPLACE INTO idempotency(key,tenant_id,route,status_code,body,created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (key, tid, request.url.path, response.status_code, payload.decode(), now_iso()))
                return JSONResponse(status_code=response.status_code, content=json.loads(payload))
            return response
        return await call_next(request)

    # -- auth dependency -------------------------------------------------------
    def ctx_from_token(authorization: str | None) -> AuthContext:
        if not authorization or not authorization.lower().startswith("bearer "):
            from ..core.errors import AuthError
            raise AuthError("missing bearer token")
        raw = authorization.split(" ", 1)[1].strip()
        ctx = application.users.context_from_token(raw)
        application.entitlements.require_feature(ctx.tenant_id, "api")
        return ctx

    async def get_ctx(request: Request) -> AuthContext:
        ctx = ctx_from_token(request.headers.get("authorization"))
        request.state.ctx = ctx
        return ctx

    api.state.get_ctx = get_ctx

    # -- routers ----------------------------------------------------------------
    from .routers import (auth, billing, dashboard, invoicing, retail, restaurant, hotel,
                          property, manufacturing, meta)
    for r in (auth, billing, dashboard, invoicing, retail, restaurant, hotel,
              property, manufacturing, meta):
        api.include_router(r.router)

    return api
