from fastapi import APIRouter, Depends, Request

from ..schemas import RoomIn, BookingIn
from .deps import get_ctx

router = APIRouter(prefix="/hotel", tags=["hotel"])


@router.get("/rooms")
def list_rooms(request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.list_rooms(ctx)


@router.post("/rooms", status_code=201)
def add_room(body: RoomIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.add_room(ctx, body.number, body.rate_cents, body.room_type)


@router.get("/availability")
def availability(check_in: str, check_out: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.availability(ctx, check_in, check_out)


@router.get("/bookings")
def list_bookings(status: str | None = None, request: Request = None, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.list_bookings(ctx, status=status)


@router.post("/bookings", status_code=201)
def create_booking(body: BookingIn, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.create_booking(
        ctx, body.guest_name, body.room_id, body.check_in, body.check_out, body.guest_phone)


@router.get("/bookings/{booking_id}")
def get_booking(booking_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.get_booking(ctx, booking_id)


@router.post("/bookings/{booking_id}/check-in")
def check_in(booking_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.check_in(ctx, booking_id)


@router.post("/bookings/{booking_id}/check-out")
def check_out(booking_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.check_out(ctx, booking_id)


@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: str, request: Request, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.cancel_booking(ctx, booking_id)


@router.get("/reports/occupancy")
def occupancy(date: str | None = None, request: Request = None, ctx=Depends(get_ctx)):
    return request.app.state.stratos.hotel.occupancy_report(ctx, date)
