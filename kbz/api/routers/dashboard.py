from fastapi import APIRouter, Depends, Request

from .deps import get_ctx

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(request: Request, ctx=Depends(get_ctx)):
    """Single call powering the Android Home screen cards."""
    return request.app.state.kbz.dashboard.summary(ctx)
