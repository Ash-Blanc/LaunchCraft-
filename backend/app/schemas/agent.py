"""Schemas for the assistant: the business brief, proposals and the changes they carry.

A proposal is the only way the assistant changes anything. It is stored, shown to
the user, and applied by trusted code only after the user accepts it.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.money import MoneyError, normalize_currency
from app.schemas.store import Brand, ProductIn, StoreConfigIn, VisualDirection, clean_text


class BusinessBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: Annotated[str, Field(min_length=1, max_length=80)]
    niche: Annotated[str, Field(min_length=3, max_length=160)]
    audience: Annotated[str, Field(max_length=200)] = ""
    personality: Annotated[str, Field(max_length=200)] = ""
    visual_direction: VisualDirection | Literal["auto"] = "auto"
    example_products: Annotated[str, Field(max_length=1200)] = ""
    price_min: Annotated[str, Field(max_length=12)] = ""
    price_max: Annotated[str, Field(max_length=12)] = ""
    currency: str = "USD"
    market: Annotated[str, Field(max_length=80)] = ""

    @field_validator("business_name", "niche", "audience", "personality", "example_products",
                     "market", "price_min", "price_max")
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


class DecisionNote(BaseModel):
    """Why the assistant made a choice — shown to the user next to the draft."""
    topic: str
    decision: str
    reason: str


class AddProduct(BaseModel):
    op: Literal["add_product"] = "add_product"
    product: ProductIn


class UpdateProduct(BaseModel):
    op: Literal["update_product"] = "update_product"
    product_id: str
    before: ProductIn  # snapshot used to detect edits made after the proposal was created
    after: ProductIn


class UpdateBrand(BaseModel):
    op: Literal["update_brand"] = "update_brand"
    before: Brand
    after: Brand


StoreChange = Annotated[AddProduct | UpdateProduct | UpdateBrand, Field(discriminator="op")]


class StoreChanges(BaseModel):
    changes: Annotated[list[StoreChange], Field(min_length=1, max_length=20)]


class GeneratedDraft(BaseModel):
    summary: str
    notes: list[DecisionNote]
    config: StoreConfigIn


class SuggestedChanges(BaseModel):
    summary: str
    rationale: str
    changes: list[StoreChange]


AgentAction = Literal["fill_missing_details", "suggest_product", "run_launch_checks"]


class MessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, Field(min_length=1, max_length=1000)]


class SuggestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: AgentAction


class StorePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    niche: Annotated[str, Field(max_length=120)] | None = None
    audience: Annotated[str, Field(max_length=200)] | None = None
    brand: Brand | None = None

    @field_validator("name", "niche", "audience")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        return clean_text(v) if v is not None else v
