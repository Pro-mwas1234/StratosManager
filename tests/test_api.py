"""REST API integration tests — the exact flows the Android app performs."""
import uuid


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


class TestAuth:
    def test_register_login_session_logout(self, client):
        r = client.post("/auth/register", json={"email": "a@b.co.ke", "password": "longenough1",
                                                 "tenant_name": "Shop A"})
        assert r.status_code == 200
        tok = r.json()["token"]
        s = client.get("/auth/session", headers=hdr(tok))
        assert s.status_code == 200 and s.json()["plan"] == "starter"
        l = client.post("/auth/login", json={"email": "a@b.co.ke", "password": "longenough1"})
        assert l.status_code == 200
        body = l.json()
        assert set(body) >= {"token", "tenant_id", "features", "plan_name"}
        # logout revokes server-side
        lo = client.post("/auth/logout", headers=hdr(body["token"]))
        assert lo.status_code == 200
        assert client.get("/me", headers=hdr(body["token"])).status_code == 401

    def test_login_bad_password_envelope(self, client):
        client.post("/auth/register", json={"email": "c@d.co.ke", "password": "longenough1",
                                            "tenant_name": "C"})
        r = client.post("/auth/login", json={"email": "c@d.co.ke", "password": "nope"})
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthenticated"

    def test_validation_short_password(self, client):
        r = client.post("/auth/register", json={"email": "x@y.z", "password": "short",
                                                "tenant_name": "T"})
        assert r.status_code == 422 or (r.status_code == 400 and
                                        r.json()["error"]["code"] == "VALIDATION")

    def test_me_shape(self, owner, client):
        h, _ = owner
        me = client.get("/me", headers=h).json()
        assert me["tenant"]["name"] == "Test Duka"
        assert "retail" in me["plan"]["features"]


class TestRetailPOS:
    def _mkproduct(self, client, h, sku="S1", price=15_000, reorder=5):
        return client.post("/retail/products", headers=h, json={
            "sku": sku, "name": f"Item {sku}", "sale_price_cents": price,
            "cost_price_cents": 9_000, "reorder_level": reorder}).json()

    def test_product_stock_sale_flow(self, owner, client):
        h, _ = owner
        p = self._mkproduct(client, h)
        adj = client.post(f"/retail/products/{p['id']}/stock", headers=h,
                          json={"delta": 10, "reason": "delivery"})
        assert adj.json()["on_hand"] == 10
        sale = client.post("/retail/sales", headers=h, json={
            "items": [{"product_id": p["id"], "qty": 3}], "payment_method": "MPESA",
            "mpesa_ref": "QGH123"})
        assert sale.status_code == 201
        assert sale.json()["total_cents"] == 45_000
        assert sale.json()["total_fmt"].startswith("KES")
        after = client.get(f"/retail/products/{p['id']}", headers=h).json()
        assert after["stock_qty"] == 7
        today = client.get("/retail/summary/today", headers=h).json()
        assert today["sales_count"] == 1 and today["total_cents"] == 45_000

    def test_oversell_conflict_409(self, owner, client):
        h, _ = owner
        p = self._mkproduct(client, h, sku="S2")
        client.post(f"/retail/products/{p['id']}/stock", headers=h, json={"delta": 2})
        r = client.post("/retail/sales", headers=h, json={
            "items": [{"product_id": p["id"], "qty": 5}]})
        assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"

    def test_negative_stock_guard(self, owner, client):
        h, _ = owner
        p = self._mkproduct(client, h, sku="S3")
        r = client.post(f"/retail/products/{p['id']}/stock", headers=h, json={"delta": -1})
        assert r.status_code == 409

    def test_low_stock_endpoint(self, owner, client):
        h, _ = owner
        p = self._mkproduct(client, h, sku="S4", reorder=5)
        client.post(f"/retail/products/{p['id']}/stock", headers=h, json={"delta": 4})
        low = client.get("/retail/stock/low", headers=h).json()
        assert any(x["sku"] == "S4" for x in low)

    def test_duplicate_sku_conflict(self, owner, client):
        h, _ = owner
        self._mkproduct(client, h, sku="DUP")
        r = client.post("/retail/products", headers=h, json={
            "sku": "dup", "name": "other", "sale_price_cents": 100})
        assert r.status_code == 409


class TestInvoicing:
    def test_invoice_vat_and_payment(self, owner, client):
        h, _ = owner
        cust = client.post("/invoices/customers", headers=h,
                           json={"name": "School", "phone": "0722333444"}).json()
        inv = client.post("/invoices/", headers=h, json={
            "customer_id": cust["id"],
            "lines": [{"description": "Books", "qty": 10, "unit_price_cents": 1_200}],
            "due_date": "2030-01-31"}).json()
        assert inv["number"].startswith("INV-")
        assert inv["net_cents"] == 12_000 and inv["vat_cents"] == 1_920
        assert inv["gross_cents"] == 13_920
        pay = client.post(f"/invoices/{inv['id']}/payments", headers=h,
                          json={"amount_cents": 13_920, "method": "MPESA",
                                "reference": "ABC"}).json()
        assert pay["status"] == "paid" and pay["balance_cents"] == 0
        again = client.post(f"/invoices/{inv['id']}/payments", headers=h,
                            json={"amount_cents": 100})
        assert again.status_code == 409

    def test_status_open_alias(self, owner, client):
        h, _ = owner
        client.post("/invoices/", headers=h, json={
            "lines": [{"description": "Service", "unit_price_cents": 5_000}]})
        lst = client.get("/invoices/?status=open", headers=h).json()
        assert len(lst) == 1 and lst[0]["status"] == "issued"

    def test_void_requires_owner_and_unpaid(self, client, stratos):
        r = client.post("/auth/register", json={"email": "o@v.ke", "password": "longenough1",
                                                "tenant_name": "V"})
        h = hdr(r.json()["token"])
        inv = client.post("/invoices/", headers=h, json={
            "lines": [{"description": "x", "unit_price_cents": 100}]}).json()
        # staff user cannot void
        client.post("/auth/staff", headers=h, json={"email": "s@v.ke", "password": "longenough1"})
        st = client.post("/auth/login", json={"email": "s@v.ke", "password": "longenough1"}).json()
        assert client.post(f"/invoices/{inv['id']}/void", headers=hdr(st["token"])).status_code == 403
        assert client.post(f"/invoices/{inv['id']}/void", headers=h).status_code == 200

    def test_aging_buckets(self, owner, client):
        h, _ = owner
        client.post("/invoices/", headers=h, json={
            "lines": [{"description": "old job", "unit_price_cents": 50_000}],
            "due_date": "2020-01-01"})
        ag = client.get("/invoices/reports/aging", headers=h).json()
        assert ag["buckets_cents"]["overdue_60_plus"] == 58_000  # +16% VAT


class TestEntitlementsAndIsolation:
    def test_starter_locked_from_restaurant(self, owner, client):
        h, _ = owner
        r = client.get("/restaurant/menu", headers=h)
        assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"

    def test_pro_unlocks_all_modules(self, pro_headers, client):
        h = pro_headers
        for path in ("/retail/products", "/invoices/customers", "/restaurant/menu",
                     "/hotel/rooms", "/property/properties", "/manufacturing/boms"):
            assert client.get(path, headers=h).status_code == 200, path

    def test_cross_tenant_isolation_matrix(self, client, stratos):
        a = client.post("/auth/register", json={"email": "a@i.ke", "password": "longenough1",
                                                "tenant_name": "A"}).json()
        b = client.post("/auth/register", json={"email": "b@i.ke", "password": "longenough1",
                                                "tenant_name": "B"}).json()
        ha, hb = hdr(a["token"]), hdr(b["token"])
        p = client.post("/retail/products", headers=ha, json={
            "sku": "X", "name": "secret item", "sale_price_cents": 500}).json()
        # B cannot read, adjust or sell A's product
        assert client.get(f"/retail/products/{p['id']}", headers=hb).status_code == 404
        assert client.post(f"/retail/products/{p['id']}/stock", headers=hb,
                           json={"delta": 5}).status_code == 404
        assert client.post("/retail/sales", headers=hb,
                           json={"items": [{"product_id": p["id"], "qty": 1}]}).status_code == 404
        assert all(x["id"] != p["id"] for x in client.get("/retail/products", headers=hb).json())
        # invoices too
        inv = client.post("/invoices/", headers=ha, json={
            "lines": [{"description": "mine", "unit_price_cents": 100}]}).json()
        assert client.get(f"/invoices/{inv['id']}", headers=hb).status_code == 404
        # dashboard never leaks counts across tenants
        db = client.get("/dashboard", headers=hb).json()
        assert db["retail"]["today_sales_count"] == 0

    def test_limit_402_on_products(self, client, stratos):
        """Starter limit is 200 products; breach → 402 LIMIT with details."""
        a = client.post("/auth/register", json={"email": "l@i.ke", "password": "longenough1",
                                                "tenant_name": "L"}).json()
        h = hdr(a["token"])
        stratos.db.exec("UPDATE tenants SET plan_id='starter' WHERE id=?", (a["user"]["tenant_id"],))
        for i in range(200):
            assert client.post("/retail/products", headers=h, json={
                "sku": f"P{i}", "name": f"p{i}", "sale_price_cents": 100}).status_code == 201
        r = client.post("/retail/products", headers=h, json={
            "sku": "P999", "name": "last", "sale_price_cents": 100})
        assert r.status_code == 402
        err = r.json()["error"]
        assert err["code"] == "payment_required" and err["details"]["limit"] == 200

    def test_staff_limit_users(self, owner, client):
        h, _ = owner  # starter allows 2 users
        assert client.post("/auth/staff", headers=h,
                           json={"email": "s1@duka.co.ke", "password": "longenough1"}).status_code == 200
        assert client.post("/auth/staff", headers=h,
                           json={"email": "s2@duka.co.ke", "password": "longenough1"}).status_code == 402


class TestIdempotency:
    def test_replay_returns_same_sale_no_double_deduct(self, owner, client):
        h, _ = owner
        p = client.post("/retail/products", headers=h, json={
            "sku": "IK", "name": "ik item", "sale_price_cents": 1_000}).json()
        client.post(f"/retail/products/{p['id']}/stock", headers=h, json={"delta": 10})
        key = str(uuid.uuid4())
        body = {"items": [{"product_id": p["id"], "qty": 2}], "payment_method": "CASH"}
        r1 = client.post("/retail/sales", headers={**h, "Idempotency-Key": key}, json=body)
        r2 = client.post("/retail/sales", headers={**h, "Idempotency-Key": key}, json=body)
        assert r1.status_code == 201
        assert r2.json() == r1.json()
        assert r2.headers.get("x-idempotent-replay") == "true"
        assert client.get(f"/retail/products/{p['id']}", headers=h).json()["stock_qty"] == 8

    def test_different_keys_are_distinct(self, owner, client):
        h, _ = owner
        p = client.post("/retail/products", headers=h, json={
            "sku": "IK2", "name": "x", "sale_price_cents": 100}).json()
        client.post(f"/retail/products/{p['id']}/stock", headers=h, json={"delta": 10})
        body = {"items": [{"product_id": p["id"], "qty": 1}]}
        r1 = client.post("/retail/sales", headers={**h, "Idempotency-Key": str(uuid.uuid4())}, json=body)
        r2 = client.post("/retail/sales", headers={**h, "Idempotency-Key": str(uuid.uuid4())}, json=body)
        assert r1.json()["id"] != r2.json()["id"]


class TestDashboard:
    def test_sections_follow_features(self, owner, pro_headers, client):
        h, _ = owner
        d = client.get("/dashboard", headers=h).json()
        assert "retail" in d and "invoicing" in d
        assert "hotel" not in d and "manufacturing" not in d
        dp = client.get("/dashboard", headers=pro_headers).json()
        assert {"retail", "invoicing", "restaurant", "hotel", "property", "manufacturing"} <= set(dp)


class TestBilling:
    def test_plans_usage_subscribe(self, owner, client):
        h, _ = owner
        plans = client.get("/billing/plans", headers=h).json()
        assert {p["id"] for p in plans} == {"starter", "growth", "pro"}
        u = client.get("/billing/usage", headers=h).json()
        assert u["plan"] == "Starter"
        sub = client.post("/billing/subscribe", headers=h, json={"plan_id": "growth"})
        assert sub.status_code == 200
        me = client.get("/me", headers=h).json()
        assert "restaurant" in me["plan"]["features"]
