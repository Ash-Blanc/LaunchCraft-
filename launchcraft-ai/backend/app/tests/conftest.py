"""Test fixtures. PayPal is replaced by an in-process fake that speaks the Orders v2 JSON shape
over httpx.MockTransport, so the real PayPalClient code path (auth, headers, errors) is exercised."""
from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from app.api import routes
from app.core.config import Settings, get_settings
from app.main import create_app
from app.models import db
from app.services.paypal import PayPalClient

TEST_SETTINGS = Settings(database_url="sqlite://", paypal_client_id="test-client",
                         paypal_client_secret="test-secret", http_timeout_seconds=2)


class FakePayPal:
    """Minimal stateful fake of PayPal Orders v2."""

    def __init__(self):
        self.orders: dict[str, dict] = {}
        self.capture_calls: list[str] = []
        self.request_ids: list[str] = []
        self.mode = "ok"  # ok | decline | underpay | timeout | pending | server_error
        self._n = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        assert request.headers.get("Authorization") == "Bearer tok"
        if rid := request.headers.get("PayPal-Request-Id"):
            self.request_ids.append(rid)

        if request.method == "POST" and path == "/v2/checkout/orders":
            body = json.loads(request.content)
            self._n += 1
            oid = f"PPORDER{self._n}"
            unit = body["purchase_units"][0]
            self.orders[oid] = {"id": oid, "status": "CREATED", "unit": unit, "captured": False}
            return httpx.Response(201, json={"id": oid, "status": "CREATED"})

        if request.method == "POST" and path.endswith("/capture"):
            oid = path.split("/")[-2]
            self.capture_calls.append(oid)
            order = self.orders.get(oid)
            if order is None:
                return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND"})
            if self.mode == "timeout":
                raise httpx.ReadTimeout("simulated", request=request)
            if self.mode == "server_error":
                return httpx.Response(503, json={"name": "SERVICE_UNAVAILABLE"})
            if self.mode == "decline":
                return httpx.Response(422, json={"name": "UNPROCESSABLE_ENTITY",
                                                 "details": [{"issue": "INSTRUMENT_DECLINED"}]})
            if order["captured"]:
                return httpx.Response(422, json={"name": "UNPROCESSABLE_ENTITY",
                                                 "details": [{"issue": "ORDER_ALREADY_CAPTURED"}]})
            order["captured"] = True
            order["status"] = "COMPLETED"
            return httpx.Response(201, json=self._representation(oid))

        if request.method == "GET" and path.startswith("/v2/checkout/orders/"):
            oid = path.split("/")[-1]
            return httpx.Response(200, json=self._representation(oid))

        return httpx.Response(404, json={"name": "NOT_FOUND"})

    def _representation(self, oid: str) -> dict:
        order = self.orders[oid]
        unit = order["unit"]
        value = unit["amount"]["value"]
        if self.mode == "underpay":
            value = f"{Decimal(value) - Decimal('1.00'):f}"
        cap_status = "PENDING" if self.mode == "pending" else "COMPLETED"
        return {"id": oid, "status": order["status"], "purchase_units": [{
            "reference_id": unit["reference_id"],
            "payments": {"captures": [{"id": f"CAP-{oid}", "status": cap_status,
                                       "amount": {"currency_code": unit["amount"]["currency_code"],
                                                  "value": value}}]}}]}


@pytest.fixture
def fake_paypal() -> FakePayPal:
    return FakePayPal()


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    db.set_engine(eng)
    return eng


@pytest.fixture
def client(engine, fake_paypal):
    app = create_app()
    paypal = PayPalClient(TEST_SETTINGS, transport=httpx.MockTransport(fake_paypal.handler))
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    app.dependency_overrides[routes.get_paypal] = lambda: paypal
    with TestClient(app) as c:
        yield c


SAMPLE_STORE = {
    "name": "Fern & Fold",
    "niche": "Small-batch botanical stationery",
    "audience": "Gift buyers who like slow, handmade things",
    "market": "United States",
    "currency": "USD",
    "brand": {"tagline": "Paper goods pressed by hand", "visual_direction": "botanical",
              "accent_color": "#3F6212"},
    "products": [
        {"slug": "pressed-fern-cards", "name": "Pressed Fern Card Set",
         "description": "Six folded cards with real pressed fern fronds under glassine, "
                        "blank inside, with recycled kraft envelopes.",
         "price": "18.00", "currency": "USD", "image_url": "/demo/fern-cards.jpg",
         "image_alt": "Six cream cards each holding a pressed green fern"},
        {"slug": "seed-paper-tags", "name": "Wildflower Seed Paper Tags",
         "description": "Twelve gift tags made from seed paper; plant them after unwrapping "
                        "and they grow into meadow flowers.",
         "price": "9.50", "currency": "USD", "image_url": "/demo/seed-tags.jpg",
         "image_alt": "Speckled paper gift tags tied with twine"},
    ],
}


@pytest.fixture
def store(client) -> dict:
    r = client.post("/api/stores", json=SAMPLE_STORE)
    assert r.status_code == 201, r.text
    return r.json()
