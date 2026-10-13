"""HTTP routes. Thin: validate input, call a service, shape output."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.db import Order, Product, Store, get_session, utcnow
from app.schemas.store import ProductIn, StoreConfigIn
from app.services.cart import CartError, CartLineRequest
from app.services.checkout import CheckoutError, cancel_checkout, capture_checkout, create_checkout
from app.services.launch_checks import run_launch_checks
from app.services.paypal import PayPalClient

router = APIRouter(prefix="/api")

_paypal: PayPalClient | None = None


def get_paypal(settings: Annotated[Settings, Depends(get_settings)]) -> PayPalClient:
    global _paypal
    if _paypal is None:
        _paypal = PayPalClient(settings)
    return _paypal


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
PayPalDep = Annotated[PayPalClient, Depends(get_paypal)]


# --- serializers -----------------------------------------------------------------
def product_out(p: Product) -> dict:
    return {"id": p.id, "slug": p.slug, "name": p.name, "description": p.description,
            "price": p.price, "currency": p.currency, "image_url": p.image_url,
            "image_alt": p.image_alt, "available": p.available, "inventory": p.inventory}


def store_out(session: Session, s: Store) -> dict:
    products = session.exec(
        select(Product).where(Product.store_id == s.id).order_by(Product.position)).all()
    return {"id": s.id, "name": s.name, "niche": s.niche, "audience": s.audience,
            "market": s.market, "currency": s.currency, "brand": s.brand,
            "products": [product_out(p) for p in products]}


def order_out(o: Order) -> dict:
    return {"id": o.id, "status": o.status.value, "currency": o.currency, "total": o.total,
            "items": o.items, "paypal_order_id": o.paypal_order_id,
            "paypal_capture_id": o.paypal_capture_id, "captured_amount": o.captured_amount,
            "failure_reason": o.failure_reason, "sandbox": o.sandbox}


def _store_or_404(session: Session, store_id: str) -> Store:
    store = session.get(Store, store_id)
    if store is None:
        raise HTTPException(404, "Store not found.")
    return store


# --- meta --------------------------------------------------------------------------
@router.get("/health")
def health(settings: SettingsDep) -> dict:
    return {"ok": True, "paypal_env": "sandbox",
            "paypal_configured": settings.paypal_configured,
            "ai_mode": "live" if settings.ai_configured else "demo"}


@router.get("/config/public")
def public_config(settings: SettingsDep) -> dict:
    # The client ID is public by design (it's loaded by the PayPal JS SDK). The secret never leaves.
    return {"paypal_client_id": settings.paypal_client_id or None, "paypal_env": "sandbox"}


# --- stores & products -----------------------------------------------------------
@router.post("/stores", status_code=201)
def create_store(body: StoreConfigIn, session: SessionDep) -> dict:
    store = Store(name=body.name, niche=body.niche, audience=body.audience, market=body.market,
                  currency=body.currency, brand=body.brand.model_dump())
    session.add(store)
    session.flush()
    for i, p in enumerate(body.products):
        session.add(Product(store_id=store.id, position=i, **p.model_dump()))
    session.commit()
    return store_out(session, store)


@router.get("/stores/{store_id}")
def get_store(store_id: str, session: SessionDep) -> dict:
    return store_out(session, _store_or_404(session, store_id))


@router.post("/stores/{store_id}/products", status_code=201)
def add_product(store_id: str, body: ProductIn, session: SessionDep) -> dict:
    store = _store_or_404(session, store_id)
    if body.currency != store.currency:
        raise HTTPException(422, f"Product currency must be {store.currency}.")
    count = len(session.exec(select(Product.id).where(Product.store_id == store_id)).all())
    product = Product(store_id=store_id, position=count, **body.model_dump())
    session.add(product)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, f"A product with slug '{body.slug}' already exists.") from None
    return product_out(product)


@router.put("/stores/{store_id}/products/{product_id}")
def update_product(store_id: str, product_id: str, body: ProductIn, session: SessionDep) -> dict:
    store = _store_or_404(session, store_id)
    product = session.get(Product, product_id)
    if product is None or product.store_id != store_id:
        raise HTTPException(404, "Product not found.")
    if body.currency != store.currency:
        raise HTTPException(422, f"Product currency must be {store.currency}.")
    for k, v in body.model_dump().items():
        setattr(product, k, v)
    store.updated_at = utcnow()
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, f"A product with slug '{body.slug}' already exists.") from None
    return product_out(product)


@router.delete("/stores/{store_id}/products/{product_id}", status_code=204)
def delete_product(store_id: str, product_id: str, session: SessionDep) -> None:
    product = session.get(Product, product_id)
    if product is None or product.store_id != store_id:
        raise HTTPException(404, "Product not found.")
    session.delete(product)
    session.commit()


# --- checkout ----------------------------------------------------------------------
class CartLineBody(BaseModel):
    product_id: Annotated[str, Field(min_length=1, max_length=64)]
    quantity: Annotated[int, Field(ge=1, le=99, strict=True)]


class CheckoutBody(BaseModel):
    # Note: no price or total fields. The server computes them.
    items: Annotated[list[CartLineBody], Field(min_length=1, max_length=50)]


@router.post("/stores/{store_id}/checkout", status_code=201)
def start_checkout(store_id: str, body: CheckoutBody, session: SessionDep,
                   paypal: PayPalDep) -> dict:
    try:
        order = create_checkout(session, paypal, store_id,
                                [CartLineRequest(i.product_id, i.quantity) for i in body.items])
    except CartError as e:
        raise HTTPException(422, str(e)) from None
    except CheckoutError as e:
        raise HTTPException(e.http_status, str(e)) from None
    return order_out(order)


@router.post("/checkout/{paypal_order_id}/capture")
def capture(paypal_order_id: str, session: SessionDep, paypal: PayPalDep) -> dict:
    try:
        return order_out(capture_checkout(session, paypal, paypal_order_id))
    except CheckoutError as e:
        raise HTTPException(e.http_status, str(e)) from None


@router.post("/checkout/{paypal_order_id}/cancel")
def cancel(paypal_order_id: str, session: SessionDep) -> dict:
    try:
        return order_out(cancel_checkout(session, paypal_order_id))
    except CheckoutError as e:
        raise HTTPException(e.http_status, str(e)) from None


# --- launch readiness ---------------------------------------------------------------
@router.post("/stores/{store_id}/launch-checks")
def launch_checks(store_id: str, session: SessionDep, settings: SettingsDep) -> dict:
    _store_or_404(session, store_id)
    report = run_launch_checks(session, settings, store_id)
    return {"id": report.id, "ready": report.ready, "results": report.results,
            "created_at": report.created_at.isoformat()}
