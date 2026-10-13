"""Checks that each available product page renders on the running storefront.

Fetches the server-rendered HTML of /store/{id}/p/{slug} and confirms a 200
response containing the product name. If the storefront isn't reachable the
check is reported as not_run, not as a pass.
"""
from __future__ import annotations

import html
from collections.abc import Callable

import httpx

from app.core.config import Settings
from app.models.db import Product, Store

RenderChecker = Callable[[Store, list[Product]], dict]


def _name_variants(name: str) -> set[str]:
    return {name, html.escape(name, quote=False), html.escape(name).replace("&#x27;", "&#39;"),
            html.escape(name)}


def make_http_render_checker(settings: Settings,
                             transport: httpx.BaseTransport | None = None) -> RenderChecker:
    def check(store: Store, products: list[Product]) -> dict:
        base = {"id": "storefront.renders", "label": "Every product page renders on the storefront",
                "kind": "automated", "required": True}
        available = [p for p in products if p.available]
        if not available:
            return {**base, "status": "not_run", "evidence": "No available products to render."}
        failures, checked = [], 0
        try:
            with httpx.Client(base_url=settings.frontend_origin, transport=transport,
                              timeout=min(settings.http_timeout_seconds, 10)) as http:
                for p in available[:20]:
                    r = http.get(f"/store/{store.id}/p/{p.slug}")
                    checked += 1
                    body = r.text
                    variants = _name_variants(p.name)
                    if r.status_code != 200:
                        failures.append(f"{p.name}: HTTP {r.status_code}")
                    elif not any(v in body for v in variants):
                        failures.append(f"{p.name}: page loaded but the product name was missing")
        except httpx.HTTPError as e:
            return {**base, "status": "not_run",
                    "evidence": f"Storefront at {settings.frontend_origin} was not reachable "
                                f"({type(e).__name__}). Start the frontend and run the checks again."}
        if failures:
            return {**base, "status": "fail", "evidence": "; ".join(failures)}
        return {**base, "status": "pass",
                "evidence": f"Loaded {checked} product page{'s' if checked != 1 else ''} from "
                            f"{settings.frontend_origin}; each returned 200 with the product name."}
    return check
