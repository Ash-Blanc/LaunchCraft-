// Display-only money helpers. The server is the source of truth for totals;
// these never feed into a payment amount.

const ZERO_DECIMAL = new Set(["JPY", "HUF", "TWD"]);

export const CURRENCIES = [
  "USD", "EUR", "GBP", "CAD", "AUD", "NZD", "SGD", "HKD", "JPY", "CHF", "SEK", "NOK", "DKK",
  "PLN", "CZK", "HUF", "MXN", "BRL", "ILS", "MYR", "PHP", "THB", "TWD", "CNY",
] as const;

export function formatPrice(amount: string, currency: string, locale = "en-US"): string {
  const n = Number(amount);
  if (!Number.isFinite(n)) return `${amount} ${currency}`;
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      minimumFractionDigits: ZERO_DECIMAL.has(currency) ? 0 : 2,
      maximumFractionDigits: ZERO_DECIMAL.has(currency) ? 0 : 2,
    }).format(n);
  } catch {
    return `${amount} ${currency}`;
  }
}

/** Estimated subtotal in minor units to avoid float drift in the display. */
export function estimateSubtotal(lines: { price: string; quantity: number }[], currency: string): string {
  const digits = ZERO_DECIMAL.has(currency) ? 0 : 2;
  const factor = 10 ** digits;
  let minor = 0;
  for (const l of lines) {
    const [whole, frac = ""] = l.price.split(".");
    const unitMinor = Number(whole) * factor + Number((frac + "00").slice(0, digits) || "0");
    minor += unitMinor * l.quantity;
  }
  return digits ? (minor / factor).toFixed(digits) : String(minor);
}
