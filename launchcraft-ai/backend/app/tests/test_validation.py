from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.money import MoneyError, format_for_paypal, parse_price
from app.schemas.store import ProductIn, StoreConfigIn
from app.tests.conftest import SAMPLE_STORE


def product(**kw):
    base = dict(slug="mug", name="Stoneware Mug",
                description="A heavy hand-thrown mug glazed in speckled oat.",
                price="24.00", currency="USD")
    base.update(kw)
    return ProductIn(**base)


class TestMoney:
    @pytest.mark.parametrize("value,currency,expected", [
        ("18", "USD", Decimal("18.00")), ("9.5", "EUR", Decimal("9.50")),
        ("1500", "JPY", Decimal("1500")), (" 0.01 ", "usd", Decimal("0.01")),
    ])
    def test_valid(self, value, currency, expected):
        assert parse_price(value, currency) == expected

    @pytest.mark.parametrize("value,currency", [
        ("0", "USD"), ("-5", "USD"), ("abc", "USD"), ("NaN", "USD"), ("Infinity", "USD"),
        ("1.999", "USD"), ("1500.5", "JPY"), ("100001", "USD"), ("10", "XYZ"), ("10", "INR"),
    ])
    def test_invalid(self, value, currency):
        with pytest.raises(MoneyError):
            parse_price(value, currency)

    def test_rejects_float(self):
        with pytest.raises(MoneyError):
            parse_price(0.1, "USD")  # type: ignore[arg-type]

    def test_paypal_format(self):
        assert format_for_paypal(Decimal("18"), "USD") == "18.00"
        assert format_for_paypal(Decimal("1500"), "JPY") == "1500"


class TestProductSchema:
    def test_normalizes(self):
        p = product(price="24", currency="usd", name="  Mug\x00 ")
        assert p.price == "24.00" and p.currency == "USD" and p.name == "Mug"

    @pytest.mark.parametrize("kw", [
        {"slug": "Bad Slug"}, {"price": "free"}, {"name": "   "},
        {"image_url": "javascript:alert(1)"}, {"image_url": "http://insecure.example/x.jpg"},
        {"image_url": "//evil.example/x.jpg"}, {"unexpected": "field"}, {"inventory": -1},
    ])
    def test_rejects(self, kw):
        with pytest.raises(ValidationError):
            product(**kw)

    def test_html_is_kept_as_plain_text(self):
        # Stored verbatim as text; React escapes it on render. No HTML is ever interpreted.
        p = product(description="<script>alert('x')</script> a mug that is plenty long enough")
        assert "<script>" in p.description


class TestStoreSchema:
    def test_sample_is_valid(self):
        assert StoreConfigIn(**SAMPLE_STORE).products[1].price == "9.50"

    def test_duplicate_slugs(self):
        data = {**SAMPLE_STORE, "products": [SAMPLE_STORE["products"][0]] * 2}
        with pytest.raises(ValidationError, match="unique"):
            StoreConfigIn(**data)

    def test_currency_mismatch(self):
        p = {**SAMPLE_STORE["products"][0], "currency": "EUR"}
        with pytest.raises(ValidationError, match="store currency"):
            StoreConfigIn(**{**SAMPLE_STORE, "products": [p]})

    def test_bad_color(self):
        with pytest.raises(ValidationError):
            StoreConfigIn(**{**SAMPLE_STORE, "brand": {"accent_color": "red;}"}})
