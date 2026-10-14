"""Live assistant: a language model behind the same StoreAgent protocol.

Trust boundary is unchanged: the model only ever *proposes*. Its output is parsed
into the same Pydantic schemas as everything else, and the user must accept the
resulting proposal before trusted code applies it.

Every call degrades gracefully: if the provider is unreachable, slow, or returns
something that fails validation, that call falls back to the deterministic demo
rules — and the response is labelled mode="demo" for that call, so the UI and the
stored proposal never claim a source that didn't produce them.

Provider: any OpenAI-compatible chat-completions endpoint (OpenAI, OpenRouter,
Together, Groq, vLLM, ...). Set AI_API_KEY, optionally AI_MODEL and AI_BASE_URL.
"""
from __future__ import annotations

import json
import re

import httpx

from app.core.config import Settings
from app.models.db import Product, Store
from app.schemas.agent import (
    AddProduct, AgentAction, BusinessBrief, GeneratedDraft, SuggestedChanges, UpdateProduct,
)
from app.schemas.store import ProductIn
from app.services.agent.base import AgentMode, MessageIntent
from app.services.agent.demo import DemoAgent
from app.services.agent.demo_catalog import CATALOGS_BY_KEY, PLACEHOLDER_IMAGE
from app.services.launch_checks import MIN_DESCRIPTION_CHARS

DEFAULT_MODEL = "gpt-4o-mini"
_CODE_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.S)
_ACTIONS: tuple[str, ...] = ("fill_missing_details", "suggest_product", "run_launch_checks")

_BUNDLED_IMAGES = sorted({
    s.image_url
    for c in CATALOGS_BY_KEY.values()
    for s in (*c.products, *c.spares)
    if s.image_url
} | {PLACEHOLDER_IMAGE})

_RULES = """Rules for every product you write:
- "slug": lowercase letters, digits and single hyphens only (e.g. "cedar-matches").
- "price": a plain decimal string for the exact currency, no symbol (e.g. "24.00").
- "currency": must equal the store currency given to you.
- "description": 1-3 plain-text sentences, no HTML, under 1200 characters.
- "image_url": either "" or one of the bundled paths listed below, or an https:// URL.
- "image_alt": one short sentence describing the photo, for screen readers.
Colors are 6-digit hex strings like "#3F6212". Reply with ONE JSON object and no other text."""


class LiveAgentError(RuntimeError):
    """Any provider or parsing failure — the caller falls back to demo rules."""


class LiveAgent:
    """mode reflects what produced the LAST call: "live", or "demo" after a fallback."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self._settings = settings
        self._transport = transport
        self._fallback = DemoAgent()
        self._last_mode: AgentMode = "live"

    @property
    def mode(self) -> AgentMode:
        return self._last_mode

    # --- provider plumbing --------------------------------------------------------
    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self._settings.http_timeout_seconds,
                            transport=self._transport)

    def _chat(self, system: str, user: str) -> dict:
        """One JSON-mode chat completion. Raises LiveAgentError on any problem."""
        body = {
            "model": self._settings.ai_model or DEFAULT_MODEL,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        try:
            with self._client() as client:
                r = client.post(
                    f"{self._settings.ai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self._settings.ai_api_key}"},
                    json=body)
        except httpx.HTTPError as e:
            raise LiveAgentError(f"provider unreachable: {e}") from e
        if r.status_code != 200:
            raise LiveAgentError(f"provider returned {r.status_code}")
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise LiveAgentError("malformed provider response") from e
        if not isinstance(content, str) or not content.strip():
            raise LiveAgentError("empty completion")
        text = _CODE_FENCE.sub("", content.strip())
        try:
            data = json.loads(text)
        except ValueError as e:
            raise LiveAgentError("completion is not valid JSON") from e
        if not isinstance(data, dict):
            raise LiveAgentError("completion is not a JSON object")
        return data

    # --- store generation ----------------------------------------------------------
    def generate_store(self, brief: BusinessBrief) -> GeneratedDraft:
        self._last_mode = "live"
        system = ("You are LaunchCraft, drafting an online store from a business brief. "
                  + _RULES)
        user = json.dumps({
            "brief": brief.model_dump(),
            "bundled_image_paths": _BUNDLED_IMAGES,
            "task": ("Return JSON {\"summary\": str, \"notes\": [{\"topic\": str, "
                     "\"decision\": str, \"reason\": str}], \"config\": {...}} where config is "
                     "the full store: name, niche, audience, market, currency, brand "
                     "{tagline, personality, visual_direction (editorial|botanical|workshop|"
                     "playful|minimal), accent_color, ink_color, surface_color} and 3-6 "
                     "products [{slug, name, description, price, currency, image_url, "
                     "image_alt}]. Honour the brief's price range, currency and visual "
                     "direction; notes explain your choices to the owner in plain language."),
        })
        try:
            data = self._chat(system, user)
            draft = GeneratedDraft.model_validate(data)
        except (LiveAgentError, ValueError) as e:  # ValueError covers pydantic ValidationError
            self._last_mode = "demo"
            return self._fallback.generate_store(brief)
        return draft

    # --- suggestions on an existing store -------------------------------------------
    def suggest(self, action: AgentAction, store: Store,
                products: list[Product]) -> SuggestedChanges | None:
        self._last_mode = "live"
        if action == "run_launch_checks":
            return None  # the API runs the checks itself; nothing to propose
        if action == "suggest_product":
            return self._suggest_product(store, products)
        return self._fill_missing(store, products)

    def _store_context(self, store: Store, products: list[Product]) -> dict:
        return {
            "store": {"name": store.name, "niche": store.niche, "audience": store.audience,
                      "market": store.market, "currency": store.currency},
            "products": [{"slug": p.slug, "name": p.name, "description": p.description,
                          "price": p.price, "image_url": p.image_url,
                          "image_alt": p.image_alt} for p in products],
        }

    def _suggest_product(self, store: Store, products: list[Product]) -> SuggestedChanges | None:
        system = ("You are LaunchCraft, suggesting ONE new product for an existing store. "
                  + _RULES)
        user = json.dumps({
            **self._store_context(store, products),
            "bundled_image_paths": _BUNDLED_IMAGES,
            "task": ("Return JSON {\"summary\": str, \"rationale\": str, \"product\": {slug, "
                     "name, description, price, currency, image_url, image_alt}} for one new "
                     "product that fits the range and doesn't duplicate an existing slug."),
        })
        try:
            data = self._chat(system, user)
            product = ProductIn.model_validate(data["product"])
            if product.currency != store.currency:
                raise ValueError(f"model used currency {product.currency}")
            taken = {p.slug for p in products}
            if product.slug in taken:
                raise ValueError(f"slug {product.slug} already exists")
            summary = str(data.get("summary") or f"Add “{product.name}”")[:200]
            rationale = str(data.get("rationale") or "")[:1200]
            return SuggestedChanges(summary=summary, rationale=rationale,
                                    changes=[AddProduct(product=product)])
        except (LiveAgentError, KeyError, TypeError, ValueError):
            self._last_mode = "demo"
            return self._fallback.suggest("suggest_product", store, products)

    def _missing(self, products: list[Product]) -> list[Product]:
        return [p for p in products
                if len(p.description) < MIN_DESCRIPTION_CHARS or not p.image_url
                or not p.image_alt]

    def _fill_missing(self, store: Store, products: list[Product]) -> SuggestedChanges | None:
        missing = self._missing(products)
        if not missing:
            return None  # nothing to do — no model call, same as demo
        system = ("You are LaunchCraft, completing incomplete product details. Write only the "
                  "fields asked for; never invent prices or change names. " + _RULES)
        user = json.dumps({
            "store": {"name": store.name, "niche": store.niche, "audience": store.audience,
                      "currency": store.currency},
            "incomplete_products": [{"slug": p.slug, "name": p.name,
                                     "description": p.description, "image_url": p.image_url,
                                     "image_alt": p.image_alt,
                                     "needs": ([("description")]
                                               if len(p.description) < MIN_DESCRIPTION_CHARS
                                               else [])
                                              + (["image_url"] if not p.image_url else [])
                                              + (["image_alt"] if not p.image_alt else [])}
                                     for p in missing],
            "bundled_image_paths": _BUNDLED_IMAGES,
            "task": ("Return JSON {\"summary\": str, \"rationale\": str, \"patches\": [{\"slug\": "
                     "str, \"description\"?: str, \"image_url\"?: str, \"image_alt\"?: str}]} — "
                     "one patch per incomplete product, only the fields it needs."),
        })
        try:
            data = self._chat(system, user)
            by_slug = {p.slug: p for p in missing}
            changes: list[UpdateProduct] = []
            for patch in data.get("patches", []):
                if not isinstance(patch, dict):
                    continue
                p = by_slug.get(patch.get("slug"))
                if p is None:
                    continue  # model patched something that isn't missing (or doesn't exist)
                before = ProductIn(slug=p.slug, name=p.name, description=p.description,
                                   price=p.price, currency=p.currency, image_url=p.image_url,
                                   image_alt=p.image_alt, available=p.available,
                                   inventory=p.inventory)
                fields = before.model_dump()
                for key in ("description", "image_url", "image_alt"):
                    if key in patch and isinstance(patch[key], str):
                        fields[key] = patch[key]
                after = ProductIn.model_validate(fields)
                if after != before:
                    changes.append(UpdateProduct(product_id=p.id, before=before, after=after))
            if not changes:
                return None
            summary = str(data.get("summary")
                          or f"Fill in missing details on {len(changes)} product(s)")[:200]
            rationale = str(data.get("rationale") or "")[:1200]
            return SuggestedChanges(summary=summary, rationale=rationale, changes=changes)
        except (LiveAgentError, TypeError, ValueError):
            self._last_mode = "demo"
            return self._fallback.suggest("fill_missing_details", store, products)

    # --- free text --------------------------------------------------------------------
    def interpret_message(self, text: str, store: Store, products: list[Product]) -> MessageIntent:
        self._last_mode = "live"
        system = ("You are LaunchCraft's storefront assistant. Route the owner's message to at "
                  "most one tool, or none. Reply with ONE JSON object: {\"reply\": str, "
                  "\"action\": \"fill_missing_details\" | \"suggest_product\" | "
                  "\"run_launch_checks\" | null}. The reply is one friendly sentence telling "
                  "the owner what you're doing (or what you can do, if action is null).")
        user = json.dumps({"store": {"name": store.name, "niche": store.niche},
                           "message": text})
        try:
            data = self._chat(system, user)
            reply = str(data.get("reply") or "").strip()
            if not reply:
                raise LiveAgentError("model returned no reply")
            action = data.get("action")
            if action not in _ACTIONS:
                action = None
            return MessageIntent(reply[:500], action)  # type: ignore[arg-type]
        except (LiveAgentError, TypeError):
            self._last_mode = "demo"
            return self._fallback.interpret_message(text, store, products)
