from app.models.db import ALLOWED_TRANSITIONS, Order, OrderStatus
from app.services.checkout import verify_capture


def ids(store):
    return {p["slug"]: p["id"] for p in store["products"]}


def start(client, store, items):
    return client.post(f"/api/stores/{store['id']}/checkout", json={"items": items})


class TestCartTotals:
    def test_server_computes_total(self, client, store):
        p = ids(store)
        r = start(client, store, [{"product_id": p["pressed-fern-cards"], "quantity": 2},
                                  {"product_id": p["seed-paper-tags"], "quantity": 3}])
        assert r.status_code == 201, r.text
        assert r.json()["total"] == "64.50"  # 2×18.00 + 3×9.50

    def test_duplicate_lines_are_merged(self, client, store):
        pid = ids(store)["seed-paper-tags"]
        r = start(client, store, [{"product_id": pid, "quantity": 1}] * 3)
        assert r.json()["items"][0]["quantity"] == 3
        assert r.json()["total"] == "28.50"

    def test_client_price_fields_rejected(self, client, store):
        pid = ids(store)["seed-paper-tags"]
        r = client.post(f"/api/stores/{store['id']}/checkout",
                        json={"items": [{"product_id": pid, "quantity": 1}], "total": "0.01"})
        # Extra field ignored; server total still authoritative.
        assert r.json()["total"] == "9.50"

    def test_paypal_receives_server_amount(self, client, store, fake_paypal):
        pid = ids(store)["pressed-fern-cards"]
        r = start(client, store, [{"product_id": pid, "quantity": 1}])
        unit = fake_paypal.orders[r.json()["paypal_order_id"]]["unit"]
        assert unit["amount"]["value"] == "18.00"
        assert unit["items"][0]["unit_amount"]["value"] == "18.00"

    def test_unavailable_product(self, client, store):
        p = store["products"][0]
        client.put(f"/api/stores/{store['id']}/products/{p['id']}",
                   json={**{k: p[k] for k in ("slug", "name", "description", "price",
                                              "currency", "image_url", "image_alt")},
                         "available": False})
        r = start(client, store, [{"product_id": p["id"], "quantity": 1}])
        assert r.status_code == 422 and "unavailable" in r.json()["detail"]

    def test_product_from_other_store(self, client, store):
        other = client.post("/api/stores", json={"name": "Other", "currency": "USD"}).json()
        r = start(client, other, [{"product_id": store["products"][0]["id"], "quantity": 1}])
        assert r.status_code == 422

    def test_bad_quantities(self, client, store):
        pid = ids(store)["seed-paper-tags"]
        for q in (0, -1, 100, 1.5, "2"):
            r = start(client, store, [{"product_id": pid, "quantity": q}])
            assert r.status_code == 422, q


class TestCaptureLifecycle:
    def test_happy_path(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["pressed-fern-cards"],
                                   "quantity": 1}]).json()
        assert o["status"] == "PAYPAL_CREATED"
        r = client.post(f"/api/checkout/{o['paypal_order_id']}/capture")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "COMPLETED"
        assert body["captured_amount"] == "18.00"
        assert body["paypal_capture_id"] == f"CAP-{o['paypal_order_id']}"
        assert f"capture-{o['id']}" in fake_paypal.request_ids

    def test_repeat_capture_is_idempotent(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        first = client.post(f"/api/checkout/{o['paypal_order_id']}/capture").json()
        second = client.post(f"/api/checkout/{o['paypal_order_id']}/capture").json()
        assert first == second
        assert fake_paypal.capture_calls.count(o["paypal_order_id"]) == 1

    def test_amount_mismatch_is_not_success(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        fake_paypal.mode = "underpay"
        body = client.post(f"/api/checkout/{o['paypal_order_id']}/capture").json()
        assert body["status"] == "FAILED"
        assert "order total" in body["failure_reason"]

    def test_pending_capture_is_not_success(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        fake_paypal.mode = "pending"
        assert client.post(f"/api/checkout/{o['paypal_order_id']}/capture").json()["status"] == "FAILED"

    def test_decline_allows_retry(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        fake_paypal.mode = "decline"
        r = client.post(f"/api/checkout/{o['paypal_order_id']}/capture")
        assert r.status_code == 402
        fake_paypal.mode = "ok"
        r = client.post(f"/api/checkout/{o['paypal_order_id']}/capture")
        assert r.json()["status"] == "COMPLETED"

    def test_timeout_allows_safe_retry(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        fake_paypal.mode = "timeout"
        assert client.post(f"/api/checkout/{o['paypal_order_id']}/capture").status_code == 503
        fake_paypal.mode = "ok"
        r = client.post(f"/api/checkout/{o['paypal_order_id']}/capture")
        assert r.json()["status"] == "COMPLETED"
        # Same PayPal-Request-Id on both attempts, so PayPal itself dedupes.
        rid = f"capture-{o['id']}"
        assert fake_paypal.request_ids.count(rid) == 2

    def test_already_captured_at_paypal_is_verified(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        fake_paypal.orders[o["paypal_order_id"]]["captured"] = True
        fake_paypal.orders[o["paypal_order_id"]]["status"] = "COMPLETED"
        body = client.post(f"/api/checkout/{o['paypal_order_id']}/capture").json()
        assert body["status"] == "COMPLETED"

    def test_unknown_order(self, client, store):
        assert client.post("/api/checkout/NOPE/capture").status_code == 404

    def test_cancel_then_capture_does_nothing(self, client, store, fake_paypal):
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        assert client.post(f"/api/checkout/{o['paypal_order_id']}/cancel").json()["status"] == "CANCELLED"
        assert client.post(f"/api/checkout/{o['paypal_order_id']}/capture").json()["status"] == "CANCELLED"
        assert fake_paypal.capture_calls == []

    def test_concurrent_capture_locked(self, client, store, engine):
        from sqlmodel import Session, select
        o = start(client, store, [{"product_id": ids(store)["seed-paper-tags"],
                                   "quantity": 1}]).json()
        with Session(engine) as s:  # simulate another request mid-capture
            order = s.exec(select(Order).where(Order.id == o["id"])).one()
            order.status = OrderStatus.CAPTURING
            s.add(order)
            s.commit()
        assert client.post(f"/api/checkout/{o['paypal_order_id']}/capture").status_code == 409

    def test_paypal_not_configured(self, engine):
        from fastapi.testclient import TestClient
        from app.api import routes
        from app.core.config import Settings, get_settings
        from app.main import create_app
        from app.services.paypal import PayPalClient
        from app.tests.conftest import SAMPLE_STORE
        bare = Settings(database_url="sqlite://")
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: bare
        app.dependency_overrides[routes.get_paypal] = lambda: PayPalClient(bare)
        with TestClient(app) as c:
            store = c.post("/api/stores", json=SAMPLE_STORE).json()
            r = c.post(f"/api/stores/{store['id']}/checkout",
                       json={"items": [{"product_id": store["products"][0]["id"], "quantity": 1}]})
            assert r.status_code == 502
            assert c.get("/api/health").json()["paypal_configured"] is False


class TestStateMachine:
    def test_terminal_states(self):
        for s in (OrderStatus.COMPLETED, OrderStatus.FAILED, OrderStatus.CANCELLED):
            assert ALLOWED_TRANSITIONS[s] == set()

    def test_cannot_complete_without_capturing(self):
        assert OrderStatus.COMPLETED not in ALLOWED_TRANSITIONS[OrderStatus.PAYPAL_CREATED]

    def test_verify_rejects_wrong_order_id(self):
        order = Order(id="a", store_id="s", currency="USD", total="10.00", paypal_order_id="P1")
        resp = {"id": "P2", "status": "COMPLETED", "purchase_units": []}
        assert not verify_capture(order, resp).ok

    def test_verify_rejects_wrong_currency(self):
        order = Order(id="a", store_id="s", currency="USD", total="10.00", paypal_order_id="P1")
        resp = {"id": "P1", "status": "COMPLETED", "purchase_units": [{"reference_id": "a",
                "payments": {"captures": [{"id": "C", "status": "COMPLETED",
                                           "amount": {"currency_code": "EUR", "value": "10.00"}}]}}]}
        assert verify_capture(order, resp).reason == "Captured currency mismatch"
