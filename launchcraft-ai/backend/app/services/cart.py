"""Trusted cart pricing. Prices always come from the database, never from the client or the AI."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import MAX_QUANTITY, quantize
from app.models.db import Product, Store


class CartError(ValueError):
    pass


@dataclass(frozen=True)
class CartLineRequest:
    product_id: str
    quantity: int


@dataclass(frozen=True)
class PricedLine:
    product_id: str
    slug: str
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

    def as_record(self) -> dict:
        return {
            "product_id": self.product_id,
            "slug": self.slug,
            "name": self.name,
            "unit_price": f"{self.unit_price:f}",
            "quantity": self.quantity,
            "line_total": f"{self.line_total:f}",
        }


@dataclass(frozen=True)
class PricedCart:
    currency: str
    lines: list[PricedLine]
    total: Decimal


def price_cart(session: Session, store_id: str, requested: list[CartLineRequest]) -> PricedCart:
    store = session.get(Store, store_id)
    if store is None:
        raise CartError("Store not found.")
    if not requested:
        raise CartError("Cart is empty.")

    # Merge duplicate lines so quantity limits can't be bypassed by splitting.
    merged: dict[str, int] = {}
    for line in requested:
        if not isinstance(line.quantity, int) or isinstance(line.quantity, bool):
            raise CartError("Quantity must be a whole number.")
        if line.quantity < 1:
            raise CartError("Quantity must be at least 1.")
        merged[line.product_id] = merged.get(line.product_id, 0) + line.quantity

    ids = list(merged)
    products = {
        p.id: p
        for p in session.exec(
            select(Product).where(Product.store_id == store_id, Product.id.in_(ids))
        )
    }

    lines: list[PricedLine] = []
    total = Decimal(0)
    for product_id, qty in merged.items():
        product = products.get(product_id)
        if product is None:
            raise CartError("A product in the cart no longer exists in this store.")
        if not product.available:
            raise CartError(f"'{product.name}' is currently unavailable.")
        if qty > MAX_QUANTITY:
            raise CartError(f"At most {MAX_QUANTITY} of '{product.name}' per order.")
        if product.inventory is not None and qty > product.inventory:
            raise CartError(f"Only {product.inventory} of '{product.name}' left.")
        if product.currency != store.currency:
            raise CartError("Product currency does not match the store currency.")
        unit = quantize(Decimal(product.price), store.currency)
        line_total = quantize(unit * qty, store.currency)
        total += line_total
        lines.append(PricedLine(product.id, product.slug, product.name, unit, qty, line_total))

    return PricedCart(currency=store.currency, lines=lines, total=quantize(total, store.currency))
