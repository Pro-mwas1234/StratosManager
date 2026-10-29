"""Seed demo tenants so the Android app has realistic Kenyan SME data to show.

Usage:
    python -m stratos.seed.seed            # seeds into KBZ_DB (default data/stratos.db)
    python -m stratos.seed.seed --reset    # delete the DB file first, then seed

Idempotent-ish: if a demo tenant email already exists it skips that tenant.
Prints login credentials + API tokens for every demo user.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta

from ..app import App
from ..core.db import now_iso

DEMO_PASSWORD = "demo1234pass"


def _today() -> date:
    return date.fromisoformat(now_iso()[:10])


def _d(days: int) -> str:
    return (_today() + timedelta(days=days)).isoformat()


def _ensure(app: App, email: str, tenant_name: str, plan_id: str):
    """Register tenant+owner unless the email already exists; returns (ctx, token)."""
    existing = app.db.one("SELECT * FROM users WHERE email=?", (email.lower(),))
    if existing:
        token = app.users.issue_token(existing["id"], kind="api")
        ctx = app.users.context_from_token(token, surface="api")
        return ctx, token, False
    user, token = app.users.register_user(email, DEMO_PASSWORD, tenant_name,
                                          phone="+254712345678", plan_id=plan_id)
    if plan_id != "starter":
        app.entitlements.subscribe(user["tenant_id"], plan_id)
    ctx = app.users.context_from_token(token, surface="api")
    return ctx, token, True


def seed_retail_invoicing(app: App) -> dict:
    """Mama Mboga Duka — starter plan: POS products + an open invoice."""
    ctx, token, created = _ensure(app, "owner@mamamboga.co.ke", "Mama Mboga Duka", "starter")
    out = {"email": "owner@mamamboga.co.ke", "token": token, "created": created}
    if not created:
        return out
    prods = [
        ("SKU-MAIZ", "Maize flour 2kg", 16_500, 13_000, "Staples", 20),
        ("SKU-RICE", "Rice basmati 1kg", 19_000, 14_500, "Staples", 20),
        ("SKU-SUGAR", "Sugar 1kg", 15_000, 12_000, "Staples", 15),
        ("SKU-OIL", "Cooking oil 1L", 22_000, 17_500, "Kitchen", 10),
        ("SKU-SOAP", "Bar soap", 6_000, 4_000, "Household", 25),
        ("SKU-MILK", "Milk 500ml", 7_000, 5_500, "Fresh", 10),
        ("SKU-BREAD", "Bread loaf", 6_500, 5_000, "Fresh", 15),
        ("SKU-SODA", "Soda 500ml", 6_000, 4_500, "Drinks", 24),
    ]
    ids = {}
    for sku, name, sale, cost, cat, reorder in prods:
        p = app.retail.create_product(ctx, sku, name, sale, cost, cat, vat_exempt=False,
                                      reorder_level=reorder)
        ids[sku] = p["id"]
        stock = 120 if cat == "Staples" else 60
        app.retail.adjust_stock(ctx, p["id"], stock, reason="opening-stock", ref="SEED")
    # milk runs low → triggers low-stock badge
    app.retail.adjust_stock(ctx, ids["SKU-MILK"], -58, reason="sale-preview", ref="SEED")
    # a couple of POS receipts today
    app.retail.create_sale(ctx, [{"product_id": ids["SKU-MAIZ"], "qty": 2},
                                 {"product_id": ids["SKU-SUGAR"], "qty": 1}], "MPESA", "QGH7XY2ZK1")
    app.retail.create_sale(ctx, [{"product_id": ids["SKU-SODA"], "qty": 3}], "CASH")
    # invoicing: customer + open invoice due in 14 days
    cust = app.invoicing.create_customer(ctx, "Green Leaf School", phone="0722000111",
                                         address="Kiambu Rd")
    app.invoicing.create_invoice(
        ctx,
        [{"description": "Maize flour 2kg x50", "qty": 50, "unit_price_cents": 16_500},
         {"description": "Cooking oil 1L x20", "qty": 20, "unit_price_cents": 22_000}],
        customer_id=cust["id"], due_date=_d(14), notes="Supply contract Q3")
    return out


def seed_restaurant(app: App) -> dict:
    """Nairobi Bites — growth plan: menu, tables, one open order."""
    ctx, token, created = _ensure(app, "owner@nairoibites.co.ke", "Nairobi Bites", "growth")
    out = {"email": "owner@nairoibites.co.ke", "token": token, "created": created}
    if not created:
        return out
    menu = [("Nyama Choma 500g", 9_50_00, "Mains"), ("Ugali & Sukuma", 4_50_00, "Mains"),
            ("Pilau", 5_50_00, "Mains"), ("Chapati (2 pc)", 2_00_00, "Sides"),
            ("Dawa cocktail", 7_00_00, "Drinks"), ("Tangawizi juice", 3_50_00, "Drinks")]
    item_ids = [app.restaurant.add_menu_item(ctx, n, c, cat)["id"] for n, c, cat in menu]
    table_ids = [app.restaurant.add_table(ctx, f"T{i}", seats=4)["id"] for i in range(1, 7)]
    order = app.restaurant.open_order(ctx, table_ids[0])
    app.restaurant.add_order_item(ctx, order["id"], item_ids[0], 2)
    app.restaurant.add_order_item(ctx, order["id"], item_ids[1], 1, notes="no sukuma extra ugali")
    app.restaurant.add_order_item(ctx, order["id"], item_ids[4], 1)
    closed = app.restaurant.open_order(ctx, table_ids[2])
    app.restaurant.add_order_item(ctx, closed["id"], item_ids[2], 2)
    app.restaurant.close_order(ctx, closed["id"], "MPESA")
    return out


def seed_hotel(app: App) -> dict:
    """Nakuru Lodge — pro plan: rooms, a checked-in guest, an arrival today."""
    ctx, token, created = _ensure(app, "manager@nakurulodge.co.ke", "Nakuru Lodge", "pro")
    out = {"email": "manager@nakurulodge.co.ke", "token": token, "created": created}
    if not created:
        return out
    rooms = []
    for i in range(1, 7):
        rtype = "deluxe" if i <= 2 else "standard"
        rate = 8_50_00 if rtype == "deluxe" else 5_50_00
        rooms.append(app.hotel.add_room(ctx, f"R{i}", rate, rtype))
    b1 = app.hotel.create_booking(ctx, "Wanjiku Kamau", rooms[0]["id"], _d(-1), _d(+2),
                                  guest_phone="+254733000111")
    app.hotel.check_in(ctx, b1["id"])
    app.hotel.create_booking(ctx, "Otieno Odhiambo", rooms[2]["id"], _d(0), _d(+3),
                             guest_phone="+254711888999")  # arrival today
    app.hotel.create_booking(ctx, "Amina Hassan", rooms[4]["id"], _d(+5), _d(+7))
    return out


def seed_property(app: App) -> dict:
    """Rift Valley Apartments — pro plan: units, leases, unpaid rent bill (arrears)."""
    ctx, token, created = _ensure(app, "owner@rvapartments.co.ke", "Rift Valley Apartments", "pro")
    out = {"email": "owner@rvapartments.co.ke", "token": token, "created": created}
    if not created:
        return out
    prop = app.property.add_property(ctx, "Sunview Flats", location="Naivasha")
    u1 = app.property.add_unit(ctx, prop["id"], "Unit 1B", 2_50_00_00)
    u2 = app.property.add_unit(ctx, prop["id"], "Unit 2A", 3_20_00_00)
    l1 = app.property.create_lease(ctx, u1["id"], "John Mwangi", _d(-90), _d(+275),
                                   deposit=50_00_00, tenant_phone="+254722111222")
    l2 = app.property.create_lease(ctx, u2["id"], "Fatuma Ali", _d(-60), _d(+305),
                                   deposit=64_00_00, tenant_phone="+254733444555")
    bill1 = app.property.issue_rent_bill(ctx, l1["id"], period=now_iso()[:7])
    app.property.record_rent_payment(ctx, bill1["id"], 2_50_00_00, "MPESA", "QKL4MN7P2")
    app.property.issue_rent_bill(ctx, l2["id"], period=now_iso()[:7], due_day=5)  # arrears
    return out


def seed_manufacturing(app: App) -> dict:
    """Juba Steelworks — pro plan: raw materials, finished door product, BOM, WIP work order."""
    ctx, token, created = _ensure(app, "ops@jubasteel.co.ke", "Juba Steelworks", "pro")
    out = {"email": "ops@jubasteel.co.ke", "token": token, "created": created}
    if not created:
        return out
    steel = app.retail.create_product(ctx, "MAT-STL", "Steel sheet 4x8", 4_50_00, 4_00_00, "Raw")
    paint = app.retail.create_product(ctx, "MAT-PNT", "Enamel paint 5L", 1_20_00, 9_50_00, "Raw")
    door = app.retail.create_product(ctx, "FG-DOOR", "Steel security door", 1_850_00, 0, "Finished")
    for pid, qty in ((steel["id"], 40), (paint["id"], 25), (door["id"], 3)):
        app.retail.adjust_stock(ctx, pid, qty, reason="opening-stock", ref="SEED")
    bom = app.manufacturing.create_bom(ctx, door["id"], [
        {"product_id": steel["id"], "qty": 2}, {"product_id": paint["id"], "qty": 0.5}])
    wo = app.manufacturing.create_work_order(ctx, bom["id"], qty_planned=5,
                                             notes="Order #A-204 for KCA office block")
    app.manufacturing.start_work_order(ctx, wo["id"])  # consumes components → in_progress
    return out


def seed_all(db_path: str | None = None) -> list[dict]:
    app = App(db_path)
    return [seed_retail_invoicing(app), seed_restaurant(app), seed_hotel(app),
            seed_property(app), seed_manufacturing(app)]


def main(argv: list[str]) -> int:
    reset = "--reset" in argv
    args = [a for a in argv if not a.startswith("--")]
    db_path = args[0] if args else None
    if reset and db_path is None:
        from ..core.db import DEFAULT_DB
        import os
        from pathlib import Path
        for suffix in ("", "-wal", "-shm"):
            p = Path(DEFAULT_DB + suffix)
            if p.exists():
                p.unlink()
        print(f"removed {DEFAULT_DB}")
    results = seed_all(db_path)
    print(json.dumps(results, indent=2))
    print("\nDemo logins (password '%s'):" % DEMO_PASSWORD)
    for r in results:
        print(f"  {r['email']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
