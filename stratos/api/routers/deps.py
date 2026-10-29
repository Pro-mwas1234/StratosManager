"""Shared helpers for routers: dependency that resolves AuthContext from request state."""
from __future__ import annotations

from fastapi import Depends, Request

from ...core.domain import AuthContext


async def get_ctx(request: Request) -> AuthContext:
    dep = request.app.state.get_ctx
    ctx = await dep(request)
    return ctx


CtxDep = Depends(get_ctx)
