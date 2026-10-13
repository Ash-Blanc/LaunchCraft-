def checks(client, store):
    r = client.post(f"/api/stores/{store['id']}/launch-checks")
    assert r.status_code == 200
    return r.json(), {c["id"]: c for c in r.json()["results"]}


def test_secret_never_exposed(client):
    for path in ("/api/health", "/api/config/public"):
        assert "test-secret" not in client.get(path).text


def test_product_crud(client, store):
    sid = store["id"]
    new = {"slug": "linen-envelopes", "name": "Linen Envelopes",
           "description": "Twenty textured linen envelopes in warm oat, sized for A6 cards.",
           "price": "7", "currency": "USD"}
    r = client.post(f"/api/stores/{sid}/products", json=new)
    assert r.status_code == 201 and r.json()["price"] == "7.00"
    pid = r.json()["id"]
    assert client.post(f"/api/stores/{sid}/products", json=new).status_code == 409
    assert client.post(f"/api/stores/{sid}/products",
                       json={**new, "slug": "x", "currency": "EUR"}).status_code == 422
    r = client.put(f"/api/stores/{sid}/products/{pid}", json={**new, "price": "8.25"})
    assert r.json()["price"] == "8.25"
    assert client.delete(f"/api/stores/{sid}/products/{pid}").status_code == 204
    assert len(client.get(f"/api/stores/{sid}").json()["products"]) == 2


def test_new_store_not_ready_until_verified_payment(client, store):
    report, by_id = checks(client, store)
    assert report["ready"] is False
    assert by_id["catalogue.not_empty"]["status"] == "pass"
    assert by_id["catalogue.complete"]["status"] == "pass"
    assert by_id["pricing.valid"]["status"] == "pass"
    assert by_id["cart.server_total"]["status"] == "pass"
    assert by_id["paypal.configured"]["status"] == "pass"
    assert by_id["paypal.capture_verified"]["status"] == "not_run"


def test_ready_after_verified_sandbox_capture(client, store):
    pid = store["products"][0]["id"]
    o = client.post(f"/api/stores/{store['id']}/checkout",
                    json={"items": [{"product_id": pid, "quantity": 1}]}).json()
    client.post(f"/api/checkout/{o['paypal_order_id']}/capture")
    report, by_id = checks(client, store)
    assert by_id["paypal.capture_verified"]["status"] == "pass"
    assert o["paypal_order_id"] in by_id["paypal.capture_verified"]["evidence"]
    assert report["ready"] is True


def test_failed_capture_does_not_count(client, store, fake_paypal):
    pid = store["products"][0]["id"]
    o = client.post(f"/api/stores/{store['id']}/checkout",
                    json={"items": [{"product_id": pid, "quantity": 1}]}).json()
    fake_paypal.mode = "underpay"
    client.post(f"/api/checkout/{o['paypal_order_id']}/capture")
    _, by_id = checks(client, store)
    assert by_id["paypal.capture_verified"]["status"] == "not_run"


def test_incomplete_products_flagged(client):
    store = client.post("/api/stores", json={"name": "Bare", "currency": "USD", "products": [
        {"slug": "thing", "name": "Thing", "description": "Too short.", "price": "5",
         "currency": "USD"}]}).json()
    _, by_id = checks(client, store)
    assert by_id["catalogue.complete"]["status"] == "fail"
    assert "no image" in by_id["catalogue.complete"]["evidence"]


def test_empty_store(client):
    store = client.post("/api/stores", json={"name": "Empty", "currency": "USD"}).json()
    report, by_id = checks(client, store)
    assert report["ready"] is False
    assert by_id["catalogue.not_empty"]["status"] == "fail"
    assert by_id["cart.server_total"]["status"] == "not_run"
