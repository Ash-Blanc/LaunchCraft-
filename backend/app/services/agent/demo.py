"""Demo assistant: rule-based and deterministic. No language model is involved.

Same input -> same output. Everything it returns is labelled mode="demo" by the API.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.core.money import SUPPORTED_CURRENCIES, MoneyError, parse_price, quantize
from app.models.db import Product, Store
from app.schemas.agent import (
    AddProduct, AgentAction, BusinessBrief, DecisionNote, GeneratedDraft, SuggestedChanges,
    UpdateProduct,
)
from app.schemas.store import Brand, ProductIn, StoreConfigIn
from app.services.agent.base import MessageIntent
from app.services.agent.demo_catalog import (
    CATALOGS_BY_KEY, PLACEHOLDER_ALT, PLACEHOLDER_IMAGE, SampleCatalog, SampleProduct,
    match_catalog,
)
from app.services.launch_checks import MIN_DESCRIPTION_CHARS

MAX_USER_PRODUCTS = 8
_PRICE_IN_LINE = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*$")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60].strip("-") or "product"


def _price_for(sample_usd: str, currency: str) -> Decimal:
    """Sample prices are written in USD-like amounts; zero-decimal currencies are scaled ×100."""
    amount = Decimal(sample_usd)
    if SUPPORTED_CURRENCIES[currency] == 0:
        amount = (amount * 100).quantize(Decimal(1))
    return quantize(amount, currency)


def _parse_range(brief: BusinessBrief) -> tuple[Decimal | None, Decimal | None]:
    lo = hi = None
    try:
        lo = parse_price(brief.price_min.replace(",", "."), brief.currency) if brief.price_min else None
    except MoneyError:
        lo = None
    try:
        hi = parse_price(brief.price_max.replace(",", "."), brief.currency) if brief.price_max else None
    except MoneyError:
        hi = None
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    return lo, hi


def parse_example_products(text: str) -> list[tuple[str, str | None]]:
    """'Mug 24, Bowl - 30' or one per line -> [(name, price-or-None)]. Max 8."""
    parts = [p.strip(" -–•*\t") for p in re.split(r"[\n;]|,(?!\d)", text)]
    items: list[tuple[str, str | None]] = []
    for part in parts:
        if not part:
            continue
        price = None
        m = _PRICE_IN_LINE.search(part)
        if m:
            price = m.group(1).replace(",", ".")
            part = part[: m.start()].rstrip(" -–:($€£¥").strip()
        name = part.strip(" -–:()")
        if len(name) >= 2:
            items.append((name[:80], price))
        if len(items) >= MAX_USER_PRODUCTS:
            break
    return items


class DemoAgent:
    mode = "demo"

    # --- store generation --------------------------------------------------------
    def generate_store(self, brief: BusinessBrief) -> GeneratedDraft:
        catalog, score = match_catalog(" ".join([brief.niche, brief.example_products]))
        notes: list[DecisionNote] = []
        if score:
            notes.append(DecisionNote(
                topic="Starting point",
                decision=f"Used the {catalog.label} sample catalogue",
                reason=f"Your niche matched {score} of its keywords."))
        else:
            notes.append(DecisionNote(
                topic="Starting point",
                decision=f"Used the {catalog.label} sample catalogue as a placeholder",
                reason="Your niche didn't match any demo catalogue closely. Replace these "
                       "products or list your own in the brief."))

        direction = catalog.direction if brief.visual_direction == "auto" else brief.visual_direction
        notes.append(DecisionNote(
            topic="Visual direction",
            decision=direction.capitalize(),
            reason="Chosen by you." if brief.visual_direction != "auto"
            else f"The default look for {catalog.label}."))

        lo, hi = _parse_range(brief)
        user_items = parse_example_products(brief.example_products)
        if user_items:
            products = self._products_from_examples(user_items, brief, catalog, lo, hi)
            notes.append(DecisionNote(
                topic="Products",
                decision=f"Drafted {len(products)} products from your examples",
                reason="Names and prices come from your list. Descriptions and photos still need "
                       "your input; the launch checks will flag them."))
        else:
            products = [self._from_sample(s, brief.currency, lo, hi) for s in catalog.products]
            notes.append(DecisionNote(
                topic="Products",
                decision=f"Added {len(products)} sample products",
                reason="You didn't list example products, so these show how a finished catalogue "
                       "looks. Edit or replace them."))
            if lo is not None or hi is not None:
                notes.append(DecisionNote(
                    topic="Pricing", decision="Kept sample prices inside your range",
                    reason="Any sample price outside the range was moved to the nearest end."))
        if SUPPORTED_CURRENCIES[brief.currency] == 0 and not user_items:
            notes.append(DecisionNote(
                topic="Currency",
                decision=f"Scaled sample prices for {brief.currency}",
                reason=f"{brief.currency} has no minor units. Review each price."))

        brand = Brand(
            tagline=brief.personality[:120] if brief.personality else catalog.tagline,
            personality=brief.personality,
            visual_direction=direction, accent_color=catalog.accent,
            ink_color=catalog.ink, surface_color=catalog.surface)
        config = StoreConfigIn(
            name=brief.business_name, niche=brief.niche, audience=brief.audience,
            market=brief.market, currency=brief.currency, brand=brand, products=products)
        return GeneratedDraft(
            summary=f"A {direction} storefront for {brief.business_name} with "
                    f"{len(products)} products in {brief.currency}.",
            notes=notes, config=config)

    def _clamp(self, price: Decimal, lo: Decimal | None, hi: Decimal | None) -> Decimal:
        if lo is not None and price < lo:
            return lo
        if hi is not None and price > hi:
            return hi
        return price

    def _from_sample(self, s: SampleProduct, currency: str, lo, hi) -> ProductIn:
        price = self._clamp(_price_for(s.price, currency), lo, hi)
        return ProductIn(slug=s.slug, name=s.name, description=s.description, price=str(price),
                         currency=currency, image_url=s.image_url, image_alt=s.image_alt)

    def _products_from_examples(self, items, brief: BusinessBrief, catalog: SampleCatalog,
                                lo, hi) -> list[ProductIn]:
        default = (lo + hi) / 2 if lo is not None and hi is not None else (
            lo or hi or _price_for(catalog.products[0].price, brief.currency))
        products, seen = [], set()
        for name, raw_price in items:
            slug = slugify(name)
            n = 2
            while slug in seen:
                slug = f"{slugify(name)[:56]}-{n}"
                n += 1
            seen.add(slug)
            try:
                price = parse_price(raw_price, brief.currency) if raw_price else quantize(default, brief.currency)
            except (MoneyError, InvalidOperation):
                price = quantize(default, brief.currency)
            products.append(ProductIn(
                slug=slug, name=name, description=f"{name} from {brief.business_name}.",
                price=str(price), currency=brief.currency))
        return products

    # --- suggestions on an existing store ----------------------------------------
    def suggest(self, action: AgentAction, store: Store,
                products: list[Product]) -> SuggestedChanges | None:
        if action == "fill_missing_details":
            return self._fill_missing(store, products)
        if action == "suggest_product":
            return self._next_product(store, products)
        return None

    def _catalog_for(self, store: Store) -> SampleCatalog:
        return match_catalog(store.niche)[0]

    def _fill_missing(self, store: Store, products: list[Product]) -> SuggestedChanges | None:
        samples = {s.slug: s for c in CATALOGS_BY_KEY.values() for s in (*c.products, *c.spares)}
        audience = store.audience.rstrip(".") if store.audience else ""
        changes = []
        for p in products:
            before = _product_in(p)
            after = before.model_copy()
            if len(p.description) < MIN_DESCRIPTION_CHARS:
                extra = f" Made with care for {audience[0].lower() + audience[1:]}." if audience else \
                    " Add what it's made of, its size and how to care for it."
                after.description = (p.description.rstrip(".") + "." + extra)[:1200]
            if not p.image_url:
                after.image_url, after.image_alt = PLACEHOLDER_IMAGE, PLACEHOLDER_ALT
            elif not p.image_alt:
                sample = samples.get(p.slug)
                after.image_alt = sample.image_alt if sample else f"Photo of {p.name}"
            if after != before:
                changes.append(UpdateProduct(product_id=p.id, before=before,
                                             after=ProductIn(**after.model_dump())))
        if not changes:
            return None
        return SuggestedChanges(
            summary=f"Fill in missing details on {len(changes)} "
                    f"product{'s' if len(changes) != 1 else ''}",
            rationale="Short descriptions get a starter sentence, products without images get a "
                      "placeholder illustration, and images without alt text get a description. "
                      "Placeholders should be replaced with real photos before launch.",
            changes=changes)

    def _next_product(self, store: Store, products: list[Product]) -> SuggestedChanges | None:
        catalog = self._catalog_for(store)
        taken = {p.slug for p in products}
        for sample in (*catalog.products, *catalog.spares):
            if sample.slug not in taken:
                product = self._from_sample(sample, store.currency, None, None)
                return SuggestedChanges(
                    summary=f"Add “{sample.name}”",
                    rationale=f"The next item from the {catalog.label} sample range, "
                              f"priced at {product.price} {store.currency}.",
                    changes=[AddProduct(product=product)])
        return None

    # --- free text ---------------------------------------------------------------
    def interpret_message(self, text: str, store: Store, products: list[Product]) -> MessageIntent:
        t = text.lower()
        if any(k in t for k in ("check", "ready", "launch", "audit")):
            return MessageIntent("Running the launch checks now.", "run_launch_checks")
        if any(k in t for k in ("missing", "alt", "describ", "fill", "image", "photo", "detail")):
            return MessageIntent("Looking for missing descriptions, images and alt text.",
                                 "fill_missing_details")
        if any(k in t for k in ("add", "new product", "another", "suggest", "more product")):
            return MessageIntent("Here's a product that fits the range.", "suggest_product")
        return MessageIntent(
            "In demo mode I follow a few fixed rules rather than a language model, so I can: "
            "suggest a product, fill in missing product details, or run the launch checks. "
            "Try one of those, or edit the catalogue directly.", None)


def _product_in(p: Product) -> ProductIn:
    return ProductIn(slug=p.slug, name=p.name, description=p.description, price=p.price,
                     currency=p.currency, image_url=p.image_url, image_alt=p.image_alt,
                     available=p.available, inventory=p.inventory)
