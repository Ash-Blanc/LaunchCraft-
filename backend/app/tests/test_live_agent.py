"""LiveAgent tests. The provider is a fake behind httpx.MockTransport — the same
pattern as FakePayPal — so the real HTTP code path (headers, timeouts, parsing,
validation, demo fallback) is exercised without network access."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api import routes
from app.core.config import Settings, get_settings
from app.main import create_app
from app.models.db import Product, Store
from app.schemas.agent import BusinessBrief
from app.services.agent import get_agent
from app.services.agent.demo import DemoAgent
from app.services.agent.live import LiveAgent

from .conftest import passing_render_check

AI_SETTINGS = Settings(database_url="sqlite://", ai_api_key="test-key",
                       ai_model="test-model", http_timeout_seconds=2)
PLAIN_SETTINGS = Settings(database_url="sqlite://")

BRIEF = BusinessBrief(business_name="Slow Kiln", niche="Small-batch stoneware ceramics",
                      audience="Slow-living gift buyers", personality="Warm and handmade",
                      currency="USD", price_min="20", price_max="80")

DRAFT_PAYLOAD = {
    "summary": "A workshop storefront for Slow Kiln with 2 products in USD.",
    "notes": [{"topic": "Products", "decision": "Drafted 2 ceramics",
               "reason": "From your niche and price range."}],
    "config": {
        "name": "Slow Kiln", "niche": "Small-batch stoneware ceramics",
        "audience": "Slow-living gift buyers", "market": "", "currency": "USD",
        "brand": {"tagline": "Fired slowly, made to last", "personality": "Warm and handmade",
                  "visual_direction": "workshop", "accent_color": "#8A5A33",
                  "ink_color": "#1C1917", "surface_color": "#FAF7F2"},
        "products": [
            {"slug": "speckled-mug", "name": "Speckled Mug",
             "description": "A sturdy stoneware mug with speckled glaze and a thrown handle.",
             "price": "28.00", "currency": "USD", "image_url": "/demo/speckled-mug.svg",
             "image_alt": "A speckled cream mug"},
            {"slug": "bud-vase", "name": "Bud Vase",
             "description": "A small matte vase for single stems, fired in a wood kiln.",
             "price": "34.00", "currency": "USD", "image_url": "", "image_alt": ""},
        ]}}


def _envelope(content) -> dict:
    text = content if isinstance(content, str) else json.dumps(content)
    return {"choices": [{"message": {"content": text}}]}


class FakeChat:
    """mode: ok | garbage | empty | http_error | timeout"""

    def __init__(self, mode="ok", payload=None):
        self.mode = mode
        self.payload = payload if payload is not None else DRAFT_PAYLOAD
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.mode == "timeout":
            raise httpx.ReadTimeout("simulated", request=request)
        if self.mode == "http_error":
            return httpx.Response(500, json={"error": "boom"})
        if self.mode == "garbage":
            return httpx.Response(200, json=_envelope("not json {{{"))
        if self.mode == "empty":
            return httpx.Response(200, json=_envelope(""))
        return httpx.Response(200, json=_envelope(self.payload))


def make_agent(fake: FakeChat) -> LiveAgent:
    return LiveAgent(AI_SETTINGS, transport=httpx.MockTransport(fake.handler))


@pytest.fixture
def incomplete_store(engine):
    """A store with one product missing description, image and alt text."""
    with Session(engine) as s:
        store = Store(name="Fern & Fold", niche="Small-batch botanical stationery",
                      audience="Gift buyers", market="United States", currency="USD",
                      brand={"tagline": "Paper goods pressed by hand",
                             "visual_direction": "botanical", "accent_color": "#3F6212"})
        s.add(store)
        s.commit()
        s.add(Product(store_id=store.id, position=0, slug="short-mug", name="Short Mug",
                      description="A mug.", price="24.00", currency="USD",
                      image_url="", image_alt=""))
        s.add(Product(store_id=store.id, position=1, slug="pressed-fern-cards",
                      name="Pressed Fern Card Set",
                      description="Six folded cards with real pressed fern fronds under "
                                  "glassine, blank inside, with recycled kraft envelopes.",
                      price="18.00", currency="USD", image_url="/demo/fern-cards.jpg",
                      image_alt="Six cream cards each holding a pressed green fern"))
        s.commit()
        return store.id


def _load(session: Session, store_id: str):
    store = session.exec(select(Store).where(Store.id == store_id)).one()
    products = list(session.exec(select(Product).where(Product.store_id == store_id)))
    return store, products


# --- factory ---------------------------------------------------------------------------
def test_get_agent_selects_by_configuration():
    assert isinstance(get_agent(AI_SETTINGS), LiveAgent)
    assert isinstance(get_agent(PLAIN_SETTINGS), DemoAgent)


# --- generate_store ---------------------------------------------------------------------
def test_generate_store_live_and_request_shape():
    fake = FakeChat()
    agent = make_agent(fake)
    draft = agent.generate_store(BRIEF)
    assert agent.mode == "live"
    assert draft.config.name == "Slow Kiln"
    assert [p.slug for p in draft.config.products] == ["speckled-mug", "bud-vase"]
    req = fake.requests[0]
    assert req.headers["Authorization"] == "Bearer test-key"
    body = json.loads(req.content)
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert str(req.url).endswith("/chat/completions")


def test_generate_store_unwraps_code_fences():
    fake = FakeChat(payload="```json\n" + json.dumps(DRAFT_PAYLOAD) + "\n```")
    agent = make_agent(fake)
    assert agent.generate_store(BRIEF).config.name == "Slow Kiln"
    assert agent.mode == "live"


@pytest.mark.parametrize("mode", ["garbage", "empty", "http_error", "timeout"])
def test_generate_store_falls_back_to_demo(mode):
    agent = make_agent(FakeChat(mode=mode))
    draft = agent.generate_store(BRIEF)
    assert agent.mode == "demo"
    assert draft.model_dump() == DemoAgent().generate_store(BRIEF).model_dump()


def test_generate_store_schema_violation_falls_back():
    bad = json.loads(json.dumps(DRAFT_PAYLOAD))
    bad["config"]["products"][0]["price"] = "free"
    agent = make_agent(FakeChat(payload=bad))
    agent.generate_store(BRIEF)
    assert agent.mode == "demo"


# --- suggest -----------------------------------------------------------------------------
def test_suggest_product_live(incomplete_store, engine):
    payload = {"summary": "Add “Fern Journal”", "rationale": "Fits the paper range.",
               "product": {"slug": "fern-journal", "name": "Fern Journal",
                           "description": "A linen-bound journal with a pressed fern cover.",
                           "price": "26.00", "currency": "USD", "image_url": "",
                           "image_alt": ""}}
    agent = make_agent(FakeChat(payload=payload))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        result = agent.suggest("suggest_product", store, products)
    assert agent.mode == "live"
    assert result.changes[0].op == "add_product"
    assert result.changes[0].product.slug == "fern-journal"


def test_suggest_product_duplicate_slug_falls_back(incomplete_store, engine):
    payload = {"summary": "x", "rationale": "y",
               "product": {"slug": "pressed-fern-cards", "name": "Duplicate",
                           "description": "This slug is already taken by another product.",
                           "price": "10.00", "currency": "USD"}}
    agent = make_agent(FakeChat(payload=payload))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        result = agent.suggest("suggest_product", store, products)
        expected = DemoAgent().suggest("suggest_product", store, products)
    assert agent.mode == "demo"
    assert result.model_dump() == expected.model_dump()


def test_fill_missing_patches_keep_db_snapshots(incomplete_store, engine):
    payload = {"summary": "Complete Short Mug", "rationale": "It was missing everything.",
               "patches": [
                   {"slug": "short-mug",
                    "description": "A speckled stoneware mug made for slow mornings.",
                    "image_url": "/demo/parcel.svg", "image_alt": "A wrapped parcel"},
                   {"slug": "does-not-exist", "description": "Ignored — not a real product."}]}
    agent = make_agent(FakeChat(payload=payload))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        result = agent.suggest("fill_missing_details", store, products)
        db_product = next(p for p in products if p.slug == "short-mug")
    assert agent.mode == "live"
    assert len(result.changes) == 1  # the unknown slug was dropped
    change = result.changes[0]
    assert change.op == "update_product"
    assert change.product_id == db_product.id
    assert change.before.description == "A mug."       # trusted snapshot from the DB
    assert change.after.description.startswith("A speckled stoneware")
    assert change.after.price == change.before.price   # model can't touch the price


def test_fill_missing_falls_back_on_garbage(incomplete_store, engine):
    agent = make_agent(FakeChat(mode="garbage"))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        result = agent.suggest("fill_missing_details", store, products)
        expected = DemoAgent().suggest("fill_missing_details", store, products)
    assert agent.mode == "demo"
    assert result.model_dump() == expected.model_dump()


# --- interpret_message -------------------------------------------------------------------
def test_interpret_message_live(incomplete_store, engine):
    payload = {"reply": "Running the launch checks now.", "action": "run_launch_checks"}
    agent = make_agent(FakeChat(payload=payload))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        intent = agent.interpret_message("are we ready?", store, products)
    assert agent.mode == "live"
    assert intent.action == "run_launch_checks"


def test_interpret_message_sanitises_unknown_action(incomplete_store, engine):
    payload = {"reply": "Hello!", "action": "launch-the-rocket"}
    agent = make_agent(FakeChat(payload=payload))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        intent = agent.interpret_message("hi", store, products)
    assert agent.mode == "live"          # sanitising is not a fallback
    assert intent.action is None
    assert intent.reply == "Hello!"


def test_interpret_message_falls_back(incomplete_store, engine):
    agent = make_agent(FakeChat(mode="http_error"))
    with Session(engine) as s:
        store, products = _load(s, incomplete_store)
        intent = agent.interpret_message("check my store", store, products)
    assert agent.mode == "demo"
    assert intent.action == "run_launch_checks"  # demo keyword rule


# --- API wiring ----------------------------------------------------------------------------
def test_api_end_to_end_live_source(engine):
    app = create_app()
    fake = FakeChat()
    live = LiveAgent(AI_SETTINGS, transport=httpx.MockTransport(fake.handler))
    app.dependency_overrides[get_settings] = lambda: AI_SETTINGS
    app.dependency_overrides[routes.get_store_agent] = lambda: live
    app.dependency_overrides[routes.get_render_checker] = lambda: passing_render_check
    with TestClient(app) as c:
        assert c.get("/api/health").json()["ai_mode"] == "live"
        r = c.post("/api/agent/draft-store", json=BRIEF.model_dump())
        assert r.status_code == 201, r.text
        proposal = r.json()
        assert proposal["source"] == "live"
        accepted = c.post(f"/api/proposals/{proposal['id']}/accept")
        assert accepted.status_code == 200, accepted.text
        store_id = accepted.json()["store"]["id"]
        store = c.get(f"/api/stores/{store_id}").json()
        assert store["name"] == "Slow Kiln"
        slugs = [p["slug"] for p in store["products"]]
        assert slugs == ["speckled-mug", "bud-vase"]
