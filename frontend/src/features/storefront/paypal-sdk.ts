"use client";

/**
 * Lazy loader for the PayPal Smart Buttons SDK.
 *
 * The script is dynamic (client-id and currency are URL params), so we cache
 * one promise per `(clientId, currency)` pair and never inject a duplicate
 * `<script>` for the same key. The PayPal SDK exposes `window.paypal.Buttons`
 * once it has finished initialising.
 */
export interface PayPalLoadOptions {
  clientId: string;
  currency: string;
  /** Override for tests. */
  scriptSrc?: string;
}

export interface PayPalApi {
  Buttons: (config: PayPalButtonsConfig) => PayPalButtonsInstance;
}

const inflight = new Map<string, Promise<PayPalApi>>();

function key(clientId: string, currency: string): string {
  return `${clientId}|${currency}`;
}

function scriptUrl(clientId: string, currency: string): string {
  const params = new URLSearchParams({
    "client-id": clientId,
    currency,
    intent: "capture",
    components: "buttons",
  });
  return `https://www.paypal.com/sdk/js?${params.toString()}`;
}

function getExisting(clientId: string, currency: string): PayPalApi | null {
  if (typeof window === "undefined") return null;
  if (!window.paypal) return null;
  if (!window.paypal.Buttons) return null;
  void clientId;
  void currency;
  return window.paypal;
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[data-paypal-sdk="${src}"]`,
    );
    if (existing) {
      if (window.paypal?.Buttons) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("PayPal SDK failed to load.")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.dataset.paypalSdk = src;
    script.addEventListener("load", () => resolve(), { once: true });
    script.addEventListener("error", () => reject(new Error("PayPal SDK failed to load.")), { once: true });
    document.head.appendChild(script);
  });
}

export function loadPayPal(options: PayPalLoadOptions): Promise<PayPalApi> {
  const { clientId, currency, scriptSrc } = options;
  const cacheKey = key(clientId, currency);
  const cached = inflight.get(cacheKey);
  if (cached) return cached;

  const promise = (async () => {
    const existing = getExisting(clientId, currency);
    if (existing) return existing;
    await loadScript(scriptSrc ?? scriptUrl(clientId, currency));
    const api = window.paypal;
    if (!api || !api.Buttons) {
      throw new Error("PayPal SDK is unavailable.");
    }
    return api;
  })();
  inflight.set(cacheKey, promise);
  return promise;
}
