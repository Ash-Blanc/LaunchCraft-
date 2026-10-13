"""Validated store configuration schemas.

Everything the AI proposes must pass through these schemas before it can reach
the database or the storefront. Text is stored as plain text (no HTML) and the
frontend renders it through React, which escapes it.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.money import MoneyError, normalize_currency, parse_price

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def clean_text(value: str) -> str:
    """Strip control characters and surrounding whitespace from untrusted text."""
    return _CONTROL_CHARS.sub("", value).strip()


ShortText = Annotated[str, Field(min_length=1, max_length=80)]
LongText = Annotated[str, Field(min_length=1, max_length=1200)]

VisualDirection = Literal["editorial", "botanical", "workshop", "playful", "minimal"]


class Brand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tagline: Annotated[str, Field(max_length=120)] = ""
    personality: Annotated[str, Field(max_length=200)] = ""
    visual_direction: VisualDirection = "editorial"
    accent_color: str = "#C2410C"
    ink_color: str = "#1C1917"
    surface_color: str = "#FAF7F2"

    @field_validator("tagline", "personality")
    @classmethod
    def _clean(cls, v: str) -> str:
        return clean_text(v)

    @field_validator("accent_color", "ink_color", "surface_color")
    @classmethod
    def _hex(cls, v: str) -> str:
        if not _HEX_COLOR.match(v):
            raise ValueError("Colors must be 6-digit hex values like #C2410C.")
        return v.upper()


class ProductIn(BaseModel):
    """Product as submitted by a user or proposed by the AI."""

    model_config = ConfigDict(extra="forbid")

    slug: Annotated[str, Field(min_length=1, max_length=60)]
    name: ShortText
    description: LongText
    price: str  # string on purpose: no floats for money
    currency: str
    image_url: Annotated[str, Field(max_length=500)] = ""
    image_alt: Annotated[str, Field(max_length=160)] = ""
    available: bool = True
    inventory: Annotated[int, Field(ge=0, le=100000)] | None = None

    @field_validator("name", "description", "image_alt")
    @classmethod
    def _clean(cls, v: str) -> str:
        return clean_text(v)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SLUG.match(v):
            raise ValueError("Slug must be lowercase letters, digits and hyphens.")
        return v

    @field_validator("currency")
    @classmethod
    def _currency(cls, v: str) -> str:
        try:
            return normalize_currency(v)
        except MoneyError as e:
            raise ValueError(str(e)) from None

    @field_validator("image_url")
    @classmethod
    def _image(cls, v: str) -> str:
        v = v.strip()
        if v and not (v.startswith("https://") or v.startswith("/")):
            raise ValueError("Image URLs must be https:// or a site-relative path.")
        if v.startswith("//"):
            raise ValueError("Protocol-relative image URLs are not allowed.")
        return v

    @model_validator(mode="after")
    def _price(self) -> "ProductIn":
        try:
            self.price = str(parse_price(self.price, self.currency))
        except MoneyError as e:
            raise ValueError(str(e)) from None
        if not self.name or not self.description:
            raise ValueError("Name and description cannot be blank.")
        return self

    @property
    def price_decimal(self) -> Decimal:
        return Decimal(self.price)


class StoreConfigIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText
    niche: Annotated[str, Field(max_length=120)] = ""
    audience: Annotated[str, Field(max_length=200)] = ""
    market: Annotated[str, Field(max_length=80)] = ""
    currency: str = "USD"
    brand: Brand = Brand()
    products: Annotated[list[ProductIn], Field(max_length=50)] = []

    @field_validator("name", "niche", "audience", "market")
    @classmethod
    def _clean(cls, v: str) -> str:
        return clean_text(v)

    @field_validator("currency")
    @classmethod
    def _currency(cls, v: str) -> str:
        try:
            return normalize_currency(v)
        except MoneyError as e:
            raise ValueError(str(e)) from None

    @model_validator(mode="after")
    def _consistent(self) -> "StoreConfigIn":
        slugs = [p.slug for p in self.products]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Product slugs must be unique within a store.")
        mismatched = [p.slug for p in self.products if p.currency != self.currency]
        if mismatched:
            raise ValueError(
                f"All products must use the store currency {self.currency}; "
                f"mismatched: {', '.join(mismatched)}."
            )
        return self
