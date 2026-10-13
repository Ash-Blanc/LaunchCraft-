import httpx
import pytest

from app.core.config import Settings
from app.models.db import Product, Store
from app.schemas.agent import BusinessBrief
from app.services.agent.demo import DemoAgent, parse_example_products
from app.services.render_check import make_http_render_checker

BRIEF = {"business_name": "Slow Kiln", "niche": "Handmade stoneware mugs and bowls",
         "audience": "Home cooks who like objects that last", "currency": "USD"}


def draft(client, **kw):
    r = client.post("/api/agent/draft-store", json={**BRIEF, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def make_store(client, **kw):
    p = draft(client, **kw)
    r = client.post(f"/api/proposals/{p['id']}/accept")
    assert r.status_code == 200, r.text
    return r.json()["store"]


class TestDemoGeneration:
    def test_deterministic(self):
        brief = BusinessBrief(**BRIEF)
        a, b = DemoAgent().generate_store(brief), DemoAgent().generate_store(brief)
        assert a.model_dump() == b.model_dump()

    def test_matches_catalog_and_labels_demo(self, client):
        p = draft(client)
        assert p["source"] == "demo" and p["status"] == "PENDING"
        cfg = p["payload"]["config"]
        assert cfg["brand"]["visual_direction"] == "workshop"
        assert [x["slug"] for x in cfg["products"]][0] == "speckled-mug"
        assert any(n["topic"] == "Starting point" for n in p["payload"]["notes"])

    def test_user_direction_wins(self, client):
        cfg = draft(client, visual_direction="minimal")["payload"]["config"]
        assert cfg["brand"]["visual_direction"] == "minimal"

    def test_price_range_clamps(self, client):
        cfg = draft(client, price_min="30", price_max="50")["payload"]["config"]
        assert all(30 <= float(p["price"]) <= 50 for p in cfg["products"])

    def test_zero_decimal_currency(self, client):
        cfg = draft(client, currency="JPY")["payload"]["config"]
        assert cfg["products"][0]["price"] == "3200"

    def test_example_products(self, client):
        cfg = draft(client, example_products="Tall latte mug - 34\nRamen bowl 42; Butter dish")[
            "payload"]["config"]
        names = [(p["name"], p["price"]) for p in cfg["products"]]
        assert names[:2] == [("Tall latte mug", "34.00"), ("Ramen bowl", "42.00")]
        assert names[2][0] == "Butter dish"

    def test_parse_examples_edge_cases(self):
        assert parse_example_products("a, Mug, Mug") == [("Mug", None), ("Mug", None)]
        assert len(parse_example_products("\n".join(f"Item {i}" for i in range(20)))) == 8

    def test_invalid_brief(self, client):
        assert client.post("/api/agent/draft-store",
                           json={**BRIEF, "currency": "INR"}).status_code == 422
        assert client.post("/api/agent/draft-store",
                           json={**BRIEF, "niche": ""}).status_code == 422

    def test_no_store_until_accepted(self, client):
        draft(client)
        assert client.get("/api/stores").json() == []


class TestProposals:
    def test_accept_creates_store_with_activity(self, client):
        store = make_store(client)
        assert store["name"] == "Slow Kiln" and len(store["products"]) == 4
        log = client.get(f"/api/stores/{store['id']}/activity").json()
        assert any(a["actor"] == "assistant (demo)" for a in log)

    def test_accept_twice(self, client):
        p = draft(client)
        client.post(f"/api/proposals/{p['id']}/accept")
        assert client.post(f"/api/proposals/{p['id']}/accept").status_code == 409

    def test_suggest_product_then_accept(self, client):
        store = make_store(client)
        r = client.post(f"/api/stores/{store['id']}/agent/suggest",
                        json={"action": "suggest_product"}).json()
        assert r["mode"] == "demo"
        pid = r["proposal"]["id"]
        # Nothing changed yet
        assert len(client.get(f"/api/stores/{store['id']}").json()["products"]) == 4
        after = client.post(f"/api/proposals/{pid}/accept").json()["store"]
        assert after["products"][-1]["slug"] == "serving-plate"

    def test_reject_changes_nothing(self, client):
        store = make_store(client)
        pid = client.post(f"/api/stores/{store['id']}/agent/suggest",
                          json={"action": "suggest_product"}).json()["proposal"]["id"]
        assert client.post(f"/api/proposals/{pid}/reject").json()["status"] == "REJECTED"
        assert len(client.get(f"/api/stores/{store['id']}").json()["products"]) == 4
        assert client.get(f"/api/stores/{store['id']}/proposals").json() == []

    def test_fill_missing_details(self, client):
        store = make_store(client, example_products="Latte mug 34")
        r = client.post(f"/api/stores/{store['id']}/agent/suggest",
                        json={"action": "fill_missing_details"}).json()
        change = r["proposal"]["payload"]["changes"][0]
        assert change["after"]["image_url"] == "/demo/parcel.svg"
        assert len(change["after"]["description"]) >= 40
        client.post(f"/api/proposals/{r['proposal']['id']}/accept")
        again = client.post(f"/api/stores/{store['id']}/agent/suggest",
                            json={"action": "fill_missing_details"}).json()
        assert again["proposal"] is None and "Nothing to suggest" in again["note"]

    def test_stale_proposal_does_not_overwrite_edit(self, client):
        store = make_store(client, example_products="Latte mug 34")
        prop = client.post(f"/api/stores/{store['id']}/agent/suggest",
                           json={"action": "fill_missing_details"}).json()["proposal"]
        p = store["products"][0]
        edited = {k: p[k] for k in ("slug", "name", "description", "price", "currency",
                                    "image_url", "image_alt", "available")}
        edited["description"] = "My own description, written by hand and long enough."
        client.put(f"/api/stores/{store['id']}/products/{p['id']}", json=edited)
        r = client.post(f"/api/proposals/{prop['id']}/accept")
        assert r.status_code == 409
        assert client.get(f"/api/proposals/{prop['id']}").json()["status"] == "STALE"
        now = client.get(f"/api/stores/{store['id']}").json()["products"][0]
        assert now["description"].startswith("My own description")

    def test_runs_out_of_suggestions(self, client):
        store = make_store(client)
        for _ in range(2):
            pid = client.post(f"/api/stores/{store['id']}/agent/suggest",
                              json={"action": "suggest_product"}).json()["proposal"]["id"]
            client.post(f"/api/proposals/{pid}/accept")
        r = client.post(f"/api/stores/{store['id']}/agent/suggest",
                        json={"action": "suggest_product"}).json()
        assert r["proposal"] is None

    def test_unknown_action_rejected(self, client):
        store = make_store(client)
        assert client.post(f"/api/stores/{store['id']}/agent/suggest",
                           json={"action": "delete_everything"}).status_code == 422


class TestMessages:
    @pytest.mark.parametrize("text,action", [
        ("are we ready to launch?", "run_launch_checks"),
        ("fill in the missing alt text", "fill_missing_details"),
        ("add another product", "suggest_product"),
        ("write me a poem", None),
    ])
    def test_routing(self, client, text, action):
        store = make_store(client)
        r = client.post(f"/api/stores/{store['id']}/agent/message", json={"text": text}).json()
        assert r["action"] == action and r["mode"] == "demo"
        if action == "run_launch_checks":
            assert r["report"]["results"]
        if action is None:
            assert "demo mode" in r["reply"]


class TestStorePatch:
    def test_patch_brand(self, client):
        store = make_store(client)
        brand = {**store["brand"], "accent_color": "#123456", "tagline": "New line"}
        r = client.patch(f"/api/stores/{store['id']}", json={"brand": brand, "name": "Kiln Two"})
        assert r.json()["brand"]["accent_color"] == "#123456" and r.json()["name"] == "Kiln Two"
        assert client.patch(f"/api/stores/{store['id']}",
                            json={"brand": {**brand, "accent_color": "blue"}}).status_code == 422
        assert client.patch(f"/api/stores/{store['id']}", json={"currency": "EUR"}).status_code == 422


class TestRenderCheck:
    def _store(self):
        s = Store(id="s1", name="Shop", currency="USD")
        return s, [Product(store_id="s1", slug="a", name="Bob's Mug & Co", description="x",
                           price="1.00", currency="USD")]

    def test_pass_with_escaped_name(self):
        s, ps = self._store()
        t = httpx.MockTransport(lambda r: httpx.Response(200, text="<h1>Bob&#x27;s Mug &amp; Co</h1>"))
        assert make_http_render_checker(Settings(), t)(s, ps)["status"] == "pass"

    def test_fail_on_404_and_missing_name(self):
        s, ps = self._store()
        t = httpx.MockTransport(lambda r: httpx.Response(404, text="nope"))
        assert make_http_render_checker(Settings(), t)(s, ps)["status"] == "fail"
        t = httpx.MockTransport(lambda r: httpx.Response(200, text="<h1>Other</h1>"))
        assert make_http_render_checker(Settings(), t)(s, ps)["status"] == "fail"

    def test_unreachable_is_not_run(self):
        s, ps = self._store()

        def boom(r):
            raise httpx.ConnectError("refused", request=r)
        result = make_http_render_checker(Settings(), httpx.MockTransport(boom))(s, ps)
        assert result["status"] == "not_run" and "not reachable" in result["evidence"]
