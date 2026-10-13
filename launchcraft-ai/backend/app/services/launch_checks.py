"""Launch-readiness checks. Every result carries evidence from an actual check.

status:  pass | fail | warn | not_run
kind:    automated            — deterministic check run by this backend
         verified_integration — proven by a real external result (e.g. a captured sandbox payment)
A check that could not be performed is reported as not_run, never as pass.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import Settings
from app.core.money import quantize
from app.models.db import LaunchReport, Order, OrderStatus, Product, Store
from app.schemas.store import ProductIn
from app.services.cart import CartError, CartLineRequest, price_cart

MIN_DESCRIPTION_CHARS = 40


def _result(check_id: str, label: str, status: str, evidence: str, *, kind: str = "automated",
            required: bool = True) -> dict:
    return {"id": check_id, "label": label, "status": status, "evidence": evidence,
            "kind": kind, "required": required}


def run_launch_checks(session: Session, settings: Settings, store_id: str,
                      extra_results: list[dict] | None = None) -> LaunchReport:
    store = session.get(Store, store_id)
    if store is None:
        raise ValueError("Store not found.")
    products = list(session.exec(
        select(Product).where(Product.store_id == store_id).order_by(Product.position)))
    available = [p for p in products if p.available]
    results: list[dict] = []

    # 1. Catalogue has something to sell
    results.append(_result(
        "catalogue.not_empty", "At least one product is available to buy",
        "pass" if available else "fail",
        f"{len(available)} of {len(products)} products are available."))

    # 2. Required product information
    missing = []
    for p in products:
        gaps = []
        if len(p.description) < MIN_DESCRIPTION_CHARS:
            gaps.append(f"description under {MIN_DESCRIPTION_CHARS} characters")
        if not p.image_url:
            gaps.append("no image")
        elif not p.image_alt:
            gaps.append("image has no alt text")
        if gaps:
            missing.append(f"{p.name}: {', '.join(gaps)}")
    results.append(_result(
        "catalogue.complete", "Every product has a description, image and alt text",
        "fail" if missing else ("pass" if products else "not_run"),
        "; ".join(missing) if missing else f"Checked {len(products)} products."))

    # 3. Prices re-validated with the same rules used on input
    invalid = []
    for p in products:
        try:
            ProductIn(slug=p.slug, name=p.name, description=p.description, price=p.price,
                      currency=p.currency, image_url=p.image_url, image_alt=p.image_alt)
        except ValidationError as e:
            invalid.append(f"{p.name}: {e.errors()[0]['msg']}")
        if p.currency != store.currency:
            invalid.append(f"{p.name}: currency {p.currency} ≠ store {store.currency}")
    results.append(_result(
        "pricing.valid", f"All prices are valid {store.currency} amounts",
        "fail" if invalid else ("pass" if products else "not_run"),
        "; ".join(invalid) if invalid else "Prices parsed as exact decimals within limits."))

    # 4. Cart math: trusted pricing equals an independent recomputation
    if available:
        try:
            cart = price_cart(session, store_id,
                              [CartLineRequest(p.id, 2) for p in available])
            expected = quantize(sum((Decimal(p.price) * 2 for p in available), Decimal(0)),
                                store.currency)
            ok = cart.total == expected
            results.append(_result(
                "cart.server_total", "Cart totals are computed by the server from stored prices",
                "pass" if ok else "fail",
                f"Sample cart of {len(available)} lines × 2: server total {cart.total} "
                f"{store.currency}, independent recomputation {expected}."))
        except CartError as e:
            results.append(_result("cart.server_total", "Cart totals are computed by the server",
                                   "fail", str(e)))
    else:
        results.append(_result("cart.server_total", "Cart totals are computed by the server",
                               "not_run", "No available products to build a test cart."))

    # 5. PayPal configuration
    results.append(_result(
        "paypal.configured", "PayPal Sandbox credentials are configured on the server",
        "pass" if settings.paypal_configured else "fail",
        "Client ID and secret present (values not shown)." if settings.paypal_configured
        else "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not set."))

    # 6. A real sandbox payment was captured and verified by the backend
    verified = session.exec(
        select(Order).where(Order.store_id == store_id, Order.status == OrderStatus.COMPLETED,
                            Order.sandbox == True)  # noqa: E712
        .order_by(Order.updated_at.desc())).first()
    if verified:
        results.append(_result(
            "paypal.capture_verified", "A sandbox payment was captured and verified by the backend",
            "pass",
            f"PayPal order {verified.paypal_order_id}, capture {verified.paypal_capture_id}, "
            f"{verified.captured_amount} {verified.currency} matched the server total.",
            kind="verified_integration"))
    else:
        results.append(_result(
            "paypal.capture_verified", "A sandbox payment was captured and verified by the backend",
            "not_run", "No verified sandbox capture yet. Complete a test checkout in the preview.",
            kind="verified_integration"))

    # 7. Results supplied by other checkers (e.g. the frontend render check)
    results.extend(extra_results or [])

    ready = all(r["status"] == "pass" for r in results if r["required"])
    report = LaunchReport(store_id=store_id, ready=ready, results=results)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report
