"""Trusted money handling. All amounts are Decimal; floats never touch prices.

Currency rules follow PayPal's documented currency list: a few currencies
(JPY, HUF, TWD) do not support decimal amounts in PayPal Checkout.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Currencies PayPal Checkout supports, mapped to the number of minor-unit digits allowed.
SUPPORTED_CURRENCIES: dict[str, int] = {
    "AUD": 2, "BRL": 2, "CAD": 2, "CNY": 2, "CZK": 2, "DKK": 2, "EUR": 2,
    "HKD": 2, "HUF": 0, "ILS": 2, "JPY": 0, "MYR": 2, "MXN": 2, "TWD": 0,
    "NZD": 2, "NOK": 2, "PHP": 2, "PLN": 2, "GBP": 2, "SGD": 2, "SEK": 2,
    "CHF": 2, "THB": 2, "USD": 2,
}

MAX_UNIT_PRICE = Decimal("100000")
MAX_QUANTITY = 99


class MoneyError(ValueError):
    pass


def normalize_currency(code: str) -> str:
    code = (code or "").strip().upper()
    if code not in SUPPORTED_CURRENCIES:
        raise MoneyError(f"Currency '{code}' is not supported by PayPal Checkout.")
    return code


def parse_price(value: str | int | Decimal, currency: str) -> Decimal:
    """Parse and validate a unit price. Rejects floats to avoid binary rounding."""
    if isinstance(value, float):
        raise MoneyError("Prices must be given as strings or Decimals, not floats.")
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise MoneyError(f"'{value}' is not a valid price.") from None
    if not amount.is_finite():
        raise MoneyError("Price must be a finite number.")
    if amount <= 0:
        raise MoneyError("Price must be greater than zero.")
    if amount > MAX_UNIT_PRICE:
        raise MoneyError(f"Price exceeds the maximum of {MAX_UNIT_PRICE}.")
    digits = SUPPORTED_CURRENCIES[normalize_currency(currency)]
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and -exponent > digits:
        raise MoneyError(f"{currency} prices allow at most {digits} decimal places.")
    return quantize(amount, currency)


def quantize(amount: Decimal, currency: str) -> Decimal:
    digits = SUPPORTED_CURRENCIES[normalize_currency(currency)]
    step = Decimal(1).scaleb(-digits)
    return amount.quantize(step, rounding=ROUND_HALF_UP)


def format_for_paypal(amount: Decimal, currency: str) -> str:
    """PayPal expects amount.value as a string with the currency's exact precision."""
    return f"{quantize(amount, currency):f}"
