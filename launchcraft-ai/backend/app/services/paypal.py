"""Thin client for the PayPal Orders v2 REST API (Sandbox only).

- OAuth token is fetched with the client secret server-side and cached until shortly before expiry.
- Every mutating call sends a PayPal-Request-Id so retries are idempotent at PayPal.
- Errors are normalized into PayPalError with PayPal's issue code when present.
The secret and access token are never logged or returned.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings


class PayPalError(Exception):
    def __init__(self, message: str, *, status: int | None = None, issue: str | None = None,
                 retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.issue = issue
        self.retryable = retryable


class PayPalNotConfigured(PayPalError):
    pass


@dataclass
class _Token:
    value: str
    expires_at: float


class PayPalClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self._settings = settings
        self._transport = transport
        self._token: _Token | None = None

    @property
    def client_id(self) -> str:
        return self._settings.paypal_client_id

    def _http(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._settings.paypal_base_url,
            timeout=self._settings.http_timeout_seconds,
            transport=self._transport,
        )

    def _access_token(self) -> str:
        if not self._settings.paypal_configured:
            raise PayPalNotConfigured("PayPal Sandbox credentials are not configured.")
        if self._token and self._token.expires_at > time.time() + 60:
            return self._token.value
        try:
            with self._http() as http:
                r = http.post(
                    "/v1/oauth2/token",
                    data={"grant_type": "client_credentials"},
                    auth=(self._settings.paypal_client_id, self._settings.paypal_client_secret),
                )
        except httpx.HTTPError as e:
            raise PayPalError(f"Could not reach PayPal: {type(e).__name__}", retryable=True) from None
        if r.status_code != 200:
            raise PayPalError("PayPal rejected the API credentials.", status=r.status_code)
        body = r.json()
        self._token = _Token(body["access_token"], time.time() + int(body.get("expires_in", 300)))
        return self._token.value

    def _request(self, method: str, path: str, *, request_id: str | None = None,
                 json: dict | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token()}",
                   "Content-Type": "application/json", "Prefer": "return=representation"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        try:
            with self._http() as http:
                r = http.request(method, path, headers=headers, json=json)
        except httpx.TimeoutException:
            raise PayPalError("PayPal did not respond in time.", retryable=True) from None
        except httpx.HTTPError as e:
            raise PayPalError(f"Could not reach PayPal: {type(e).__name__}", retryable=True) from None

        if r.status_code == 401:
            self._token = None
        if r.status_code >= 400:
            issue = None
            try:
                details = r.json().get("details") or []
                issue = details[0].get("issue") if details else r.json().get("name")
            except ValueError:
                pass
            raise PayPalError(f"PayPal returned HTTP {r.status_code}.", status=r.status_code,
                              issue=issue, retryable=r.status_code >= 500)
        return r.json()

    # --- Orders v2 ---------------------------------------------------------------
    def create_order(self, *, reference_id: str, currency: str, total: str,
                     items: list[dict]) -> dict:
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": reference_id,
                "custom_id": reference_id,
                "amount": {
                    "currency_code": currency,
                    "value": total,
                    "breakdown": {"item_total": {"currency_code": currency, "value": total}},
                },
                "items": [{
                    "name": i["name"][:127],
                    "quantity": str(i["quantity"]),
                    "unit_amount": {"currency_code": currency, "value": i["unit_price"]},
                    "sku": i["slug"][:127],
                } for i in items],
            }],
        }
        return self._request("POST", "/v2/checkout/orders",
                             request_id=f"create-{reference_id}", json=body)

    def capture_order(self, paypal_order_id: str, *, reference_id: str) -> dict:
        return self._request("POST", f"/v2/checkout/orders/{paypal_order_id}/capture",
                             request_id=f"capture-{reference_id}", json={})

    def get_order(self, paypal_order_id: str) -> dict:
        return self._request("GET", f"/v2/checkout/orders/{paypal_order_id}")
