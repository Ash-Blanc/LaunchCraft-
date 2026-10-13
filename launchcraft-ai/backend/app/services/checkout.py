"""Checkout lifecycle: create PayPal order -> buyer approves -> backend captures and verifies.

A payment is only recorded as COMPLETED when PayPal's capture response says
COMPLETED *and* the captured amount and currency exactly match what this
backend computed from trusted product data.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import update
from sqlmodel import Session, select

from app.core.money import format_for_paypal
from app.models.db import ALLOWED_TRANSITIONS, Order, OrderStatus, utcnow
from app.services.cart import CartLineRequest, price_cart
from app.services.paypal import PayPalClient, PayPalError


class CheckoutError(Exception):
    def __init__(self, message: str, *, http_status: int = 400):
        super().__init__(message)
        self.http_status = http_status


def _transition(session: Session, order: Order, new: OrderStatus, **fields) -> Order:
    """Atomic compare-and-set on status. Fails if another request moved the order first."""
    if new not in ALLOWED_TRANSITIONS[order.status]:
        raise CheckoutError(f"Order cannot move from {order.status.value} to {new.value}.",
                            http_status=409)
    result = session.exec(
        update(Order)
        .where(Order.id == order.id, Order.status == order.status)
        .values(status=new, updated_at=utcnow(), **fields)
    )
    if result.rowcount != 1:
        session.rollback()
        raise CheckoutError("This order is already being processed.", http_status=409)
    session.commit()
    session.refresh(order)
    return order


def create_checkout(session: Session, paypal: PayPalClient, store_id: str,
                    lines: list[CartLineRequest]) -> Order:
    cart = price_cart(session, store_id, lines)
    order = Order(store_id=store_id, currency=cart.currency,
                  total=format_for_paypal(cart.total, cart.currency),
                  items=[line.as_record() for line in cart.lines])
    session.add(order)
    session.commit()
    session.refresh(order)

    items = [{**line.as_record(),
              "unit_price": format_for_paypal(line.unit_price, cart.currency)}
             for line in cart.lines]
    try:
        pp = paypal.create_order(reference_id=order.id, currency=order.currency,
                                 total=order.total, items=items)
    except PayPalError as e:
        _transition(session, order, OrderStatus.FAILED, failure_reason=f"create: {e}")
        raise CheckoutError("PayPal could not create the order. Please try again.",
                            http_status=502) from None

    pp_id = pp.get("id")
    if not pp_id or pp.get("status") not in {"CREATED", "PAYER_ACTION_REQUIRED"}:
        _transition(session, order, OrderStatus.FAILED,
                    failure_reason=f"unexpected create status {pp.get('status')}")
        raise CheckoutError("PayPal returned an unexpected order state.", http_status=502)
    order.paypal_order_id = pp_id
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@dataclass(frozen=True)
class CaptureVerification:
    ok: bool
    capture_id: str | None
    amount: str | None
    reason: str | None


def verify_capture(order: Order, response: dict) -> CaptureVerification:
    """Pure function: decide whether a PayPal capture response proves payment for this order."""
    if response.get("id") != order.paypal_order_id:
        return CaptureVerification(False, None, None, "PayPal order id mismatch")
    if response.get("status") != "COMPLETED":
        return CaptureVerification(False, None, None,
                                   f"PayPal order status is {response.get('status')}")
    try:
        unit = response["purchase_units"][0]
        capture = unit["payments"]["captures"][0]
    except (KeyError, IndexError, TypeError):
        return CaptureVerification(False, None, None, "No capture found in PayPal response")
    if unit.get("reference_id") not in (None, order.id):
        return CaptureVerification(False, None, None, "Reference id mismatch")
    if capture.get("status") != "COMPLETED":
        return CaptureVerification(False, capture.get("id"), None,
                                   f"Capture status is {capture.get('status')}")
    amount = capture.get("amount") or {}
    if amount.get("currency_code") != order.currency:
        return CaptureVerification(False, capture.get("id"), None, "Captured currency mismatch")
    try:
        paid = Decimal(str(amount.get("value")))
    except InvalidOperation:
        return CaptureVerification(False, capture.get("id"), None, "Captured amount unreadable")
    if paid != Decimal(order.total):
        return CaptureVerification(False, capture.get("id"), f"{paid:f}",
                                   f"Captured {paid} but order total is {order.total}")
    return CaptureVerification(True, capture.get("id"), f"{paid:f}", None)


def capture_checkout(session: Session, paypal: PayPalClient, paypal_order_id: str) -> Order:
    order = session.exec(select(Order).where(Order.paypal_order_id == paypal_order_id)).first()
    if order is None:
        raise CheckoutError("Unknown order.", http_status=404)

    # Idempotent replay: a finished order returns its recorded outcome, never re-captures.
    if order.status in (OrderStatus.COMPLETED, OrderStatus.FAILED, OrderStatus.CANCELLED):
        return order

    order = _transition(session, order, OrderStatus.CAPTURING)  # lock; 409 if concurrent

    try:
        response = paypal.capture_order(paypal_order_id, reference_id=order.id)
    except PayPalError as e:
        if e.issue == "ORDER_ALREADY_CAPTURED":
            response = paypal.get_order(paypal_order_id)
        elif e.issue == "INSTRUMENT_DECLINED" or e.retryable:
            # Buyer can pick another funding source / we can safely retry with the same request id.
            _transition(session, order, OrderStatus.PAYPAL_CREATED)
            raise CheckoutError(
                "The payment method was declined. Please choose another."
                if e.issue == "INSTRUMENT_DECLINED"
                else "PayPal is temporarily unreachable. Your card was not charged twice; try again.",
                http_status=402 if e.issue == "INSTRUMENT_DECLINED" else 503,
            ) from None
        else:
            _transition(session, order, OrderStatus.FAILED,
                        failure_reason=f"capture: {e.issue or e}")
            raise CheckoutError("PayPal could not capture this payment.", http_status=502) from None

    result = verify_capture(order, response)
    if result.ok:
        return _transition(session, order, OrderStatus.COMPLETED,
                           paypal_capture_id=result.capture_id, captured_amount=result.amount)
    return _transition(session, order, OrderStatus.FAILED, paypal_capture_id=result.capture_id,
                       captured_amount=result.amount, failure_reason=result.reason)


def cancel_checkout(session: Session, paypal_order_id: str) -> Order:
    order = session.exec(select(Order).where(Order.paypal_order_id == paypal_order_id)).first()
    if order is None:
        raise CheckoutError("Unknown order.", http_status=404)
    if order.status == OrderStatus.CANCELLED:
        return order
    return _transition(session, order, OrderStatus.CANCELLED, failure_reason="buyer cancelled")
