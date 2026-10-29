"""Hotel: rooms, bookings with date-overlap conflict detection, check-in/out."""
from __future__ import annotations

from datetime import date, timedelta

from ..core.db import Database, new_id, now_iso
from ..core.errors import ConflictError, ValidationError
from ..core.money import fmt_kes, parse_amount
from ..billing.entitlements import EntitlementService
from ..core.domain import AuthContext

MODULE = "hotel"


def _valid_date(s: str, field: str) -> str:
    try:
        return date.fromisoformat(s).isoformat()
    except (ValueError, TypeError):
        raise ValidationError(f"{field} must be YYYY-MM-DD, got '{s}'")


class HotelService:
    def __init__(self, db: Database, ent: EntitlementService):
        self.db = db
        self.ent = ent

    def _guard(self, ctx: AuthContext, write: bool = True) -> None:
        self.ent.require_feature(ctx.tenant_id, MODULE)

    # -- rooms ---------------------------------------------------------------
    def add_room(self, ctx: AuthContext, number: str, rate, room_type: str = "standard") -> dict:
        self._guard(ctx)
        if not number.strip():
            raise ValidationError("room number required")
        rid = self.db.tenant_insert("rooms", ctx.tenant_id, {
            "number": number.strip().upper(), "room_type": room_type,
            "rate_cents": parse_amount(rate)})
        return self.db.tenant_get("rooms", ctx.tenant_id, rid)

    def list_rooms(self, ctx: AuthContext) -> list[dict]:
        self._guard(ctx, write=False)
        return self.db.tenant_rows("rooms", ctx.tenant_id, order="number ASC")

    # -- bookings --------------------------------------------------------------
    def create_booking(self, ctx: AuthContext, guest_name: str, room_id: str,
                       check_in: str, check_out: str, guest_phone: str | None = None) -> dict:
        self._guard(ctx)
        self.ent.check_limit(ctx.tenant_id, "documents_per_month")
        ci, co = _valid_date(check_in, "check_in"), _valid_date(check_out, "check_out")
        if co <= ci:
            raise ValidationError("check_out must be after check_in")
        room = self.db.tenant_get("rooms", ctx.tenant_id, room_id)
        if self.room_occupied(ctx, room_id, ci, co):
            raise ConflictError(f"room {room['number']} already booked for those dates")
        nights = (date.fromisoformat(co) - date.fromisoformat(ci)).days
        total = room["rate_cents"] * nights
        bid = self.db.tenant_insert("bookings", ctx.tenant_id, {
            "guest_name": guest_name.strip(), "guest_phone": guest_phone, "room_id": room_id,
            "check_in_date": ci, "check_out_date": co, "status": "reserved",
            "nights": nights, "total_cents": total})
        self.ent.meter(ctx.tenant_id, "documents_per_month", ref=f"BKG-{bid}")
        return self.get_booking(ctx, bid)

    def get_booking(self, ctx: AuthContext, booking_id: str) -> dict:
        b = self.db.tenant_get("bookings", ctx.tenant_id, booking_id)
        b["total_fmt"] = fmt_kes(b["total_cents"])
        return b

    def room_occupied(self, ctx: AuthContext, room_id: str, ci: str, co: str) -> bool:
        """Half-open interval overlap: [check_in, check_out)."""
        rows = self.db.query(
            "SELECT id FROM bookings WHERE tenant_id=? AND room_id=? "
            "AND status IN ('reserved','checked_in') AND check_in_date < ? AND check_out_date > ?",
            (ctx.tenant_id, room_id, co, ci))
        return bool(rows)

    def availability(self, ctx: AuthContext, ci: str, co: str) -> list[dict]:
        self._guard(ctx, write=False)
        out = []
        for r in self.db.tenant_rows("rooms", ctx.tenant_id, order="number ASC"):
            free = not self.room_occupied(ctx, r["id"], _valid_date(ci, "check_in"),
                                          _valid_date(co, "check_out"))
            out.append({"room": r["number"], "type": r["room_type"],
                        "rate_cents": r["rate_cents"], "free": free})
        return out

    def check_in(self, ctx: AuthContext, booking_id: str) -> dict:
        b = self.db.tenant_get("bookings", ctx.tenant_id, booking_id)
        if b["status"] != "reserved":
            raise ConflictError(f"booking is {b['status']}, cannot check in")
        today = now_iso()[:10]
        if b["check_in_date"] > today:
            raise ValidationError(f"check-in starts {b['check_in_date']}; too early")
        return self.db.tenant_update("bookings", ctx.tenant_id, booking_id, {"status": "checked_in"})

    def check_out(self, ctx: AuthContext, booking_id: str) -> dict:
        b = self.db.tenant_get("bookings", ctx.tenant_id, booking_id)
        if b["status"] != "checked_in":
            raise ConflictError(f"booking is {b['status']}, cannot check out")
        return self.db.tenant_update("bookings", ctx.tenant_id, booking_id, {"status": "completed"})

    def cancel_booking(self, ctx: AuthContext, booking_id: str) -> dict:
        b = self.db.tenant_get("bookings", ctx.tenant_id, booking_id)
        if b["status"] == "completed":
            raise ConflictError("cannot cancel a completed stay")
        return self.db.tenant_update("bookings", ctx.tenant_id, booking_id, {"status": "cancelled"})

    def list_bookings(self, ctx: AuthContext, status: str | None = None, limit: int = 100) -> list[dict]:
        self._guard(ctx, write=False)
        where, params = "", ()
        if status:
            where, params = "status=?", (status,)
        return self.db.tenant_rows("bookings", ctx.tenant_id, where=where, params=params, limit=limit)

    def occupancy_report(self, ctx: AuthContext, on_date: str | None = None) -> dict:
        d = _valid_date(on_date or now_iso()[:10], "on_date")
        tomorrow = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        rooms = self.db.tenant_rows("rooms", ctx.tenant_id)
        occupied = sum(1 for r in rooms if self.room_occupied(ctx, r["id"], d, tomorrow))
        pct = round(100 * occupied / len(rooms)) if rooms else 0
        return {"date": d, "rooms_total": len(rooms), "rooms_occupied": occupied, "occupancy_pct": pct}
