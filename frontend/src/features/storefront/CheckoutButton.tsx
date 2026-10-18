"use client";

/**
 * PayPal Smart Buttons wired to the backend `create-checkout` / `capture` /
 * `cancel` flow.
 *
 * Trust model: the cart lines never carry prices — the server reads current
 * product data and computes the total. We only ever tell PayPal *which*
 * PayPal order to capture, never what to charge it.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError, errorMessage } from "@/lib/api";
import type { CartLine } from "./cart";
import { loadPayPal } from "./paypal-sdk";

export interface CheckoutButtonProps {
  storeId: string;
  currency: string;
  /** Lines to charge for. Quantity is reused; everything else is server-pricing. */
  lines: CartLine[];
  onCartCleared?: () => void;
}

type Status =
  | { kind: "loading-config" }
  | { kind: "loading-sdk"; message: string }
  | { kind: "ready" }
  | { kind: "creating-order" }
  | { kind: "capturing" }
  | { kind: "completed"; paypalOrderId: string }
  | { kind: "unavailable"; message: string }
  | { kind: "error"; message: string };

const SDK_TIMEOUT_MS = 15_000;

export function CheckoutButton({ storeId, currency, lines, onCartCleared }: CheckoutButtonProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<Status>({ kind: "loading-config" });
  const paypalOrderIdRef = useRef<string | null>(null);

  const requestedAmount = useMemo(
    () => lines.reduce((n, l) => n + l.quantity, 0),
    [lines],
  );

  // Pull a browser-safe PayPal client id from the backend, load the SDK, render buttons.
  // Re-runs when cart contents change (so a fresh order is created against the new total).
  useEffect(() => {
    let cancelled = false;
    paypalOrderIdRef.current = null;
    (async () => {
      try {
        const cfg = await api.publicConfig();
        if (cancelled) return;
        if (!cfg.paypal_client_id) {
          setStatus({
            kind: "unavailable",
            message: "PayPal Sandbox isn't configured on this backend yet.",
          });
          return;
        }
        setStatus({ kind: "loading-sdk", message: "Loading PayPal…" });
        const sdk = await loadPayPal({ clientId: cfg.paypal_client_id, currency });
        if (cancelled) return;
        const container = containerRef.current;
        if (!container) return;
        // Wipe any previously rendered buttons so a stale SDK instance can't capture a stale total.
        container.replaceChildren();
        await sdk.Buttons({
          createOrder: async () => {
            setStatus({ kind: "creating-order" });
            try {
              const order = await api.startCheckout(storeId, lines.map((l) => ({
                product_id: l.productId,
                quantity: l.quantity,
              })));
              if (!order.paypal_order_id) {
                throw new Error("PayPal did not return an order id.");
              }
              paypalOrderIdRef.current = order.paypal_order_id;
              setStatus({ kind: "ready" });
              return order.paypal_order_id;
            } catch (e) {
              const message = e instanceof ApiError && e.status === 422
                ? "One of these items isn't available anymore — refresh and try again."
                : errorMessage(e);
              setStatus({ kind: "error", message });
              throw e;
            }
          },
          onApprove: async () => {
            const id = paypalOrderIdRef.current;
            if (!id) {
              setStatus({ kind: "error", message: "We lost track of that payment. Try again." });
              return;
            }
            setStatus({ kind: "capturing" });
            try {
              const order = await api.captureCheckout(id);
              if (order.status === "COMPLETED") {
                setStatus({ kind: "completed", paypalOrderId: id });
                onCartCleared?.();
                return;
              }
              const detail = order.failure_reason ?? `Order ended as ${order.status}.`;
              setStatus({ kind: "error", message: `Payment didn't complete: ${detail}` });
            } catch (e) {
              setStatus({ kind: "error", message: errorMessage(e) });
            }
          },
          onCancel: async (data) => {
            try {
              await api.cancelCheckout(data.orderID);
            } catch {
              /* The order stays in PAYPAL_CREATED — the buyer can resume from PayPal. */
            }
            setStatus({ kind: "ready" });
          },
          onError: (err) => {
            setStatus({ kind: "error", message: err.message || "PayPal couldn't start the checkout." });
          },
          style: { layout: "vertical", color: "gold", shape: "rect", height: 48, label: "pay", tagline: false },
        }).render(container);
        if (!cancelled) setStatus({ kind: "ready" });
      } catch (e) {
        const message = e instanceof Error ? e.message : "PayPal couldn't load here.";
        if (!cancelled) setStatus({ kind: "unavailable", message });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storeId, currency, lines, onCartCleared]);

  // SDK scripts can hang on slow networks; if we don't hear back, surface a useful message.
  useEffect(() => {
    if (status.kind !== "loading-sdk") return;
    const timer = window.setTimeout(() => {
      setStatus((prev) => prev.kind === "loading-sdk"
        ? { kind: "unavailable", message: "PayPal took too long to load. Refresh the page to try again." }
        : prev);
    }, SDK_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [status.kind]);

  const handleRetry = useCallback(() => {
    window.location.reload();
  }, []);

  return (
    <div className="w-full">
      <div ref={containerRef} aria-label="PayPal checkout" className="min-h-12" />
      <StatusNotice status={status} cartEmpty={requestedAmount === 0} onRetry={handleRetry} />
    </div>
  );
}

function StatusNotice({ status, cartEmpty, onRetry }: {
  status: Status;
  cartEmpty: boolean;
  onRetry: () => void;
}) {
  if (cartEmpty) {
    return (
      <p className="mt-2 text-xs leading-relaxed text-[color:var(--s-muted)]" role="status">
        Add at least one item to your cart before checking out.
      </p>
    );
  }
  switch (status.kind) {
    case "loading-config":
    case "loading-sdk":
    case "ready":
    case "creating-order":
    case "capturing":
      return (
        <p className="mt-2 text-xs leading-relaxed text-[color:var(--s-muted)]" role="status">
          {status.kind === "loading-config" && "Checking PayPal availability…"}
          {status.kind === "loading-sdk" && status.message}
          {status.kind === "ready" && "PayPal is ready. Pay with PayPal or a card — no PayPal account needed for sandbox purchases."}
          {status.kind === "creating-order" && "Reserving your total with the server…"}
          {status.kind === "capturing" && "Verifying the payment with PayPal…"}
        </p>
      );
    case "completed":
      return (
        <p className="mt-2 text-xs leading-relaxed text-[color:var(--pass)]" role="status">
          Payment received. Your cart has been cleared.
        </p>
      );
    case "unavailable":
      return (
        <div className="mt-2 text-xs leading-relaxed text-[color:var(--s-muted)]" role="status">
          <p>{status.message}</p>
          <button type="button" onClick={onRetry}
            className="mt-1 underline underline-offset-4 hover:text-[color:var(--s-ink)]">
            Retry
          </button>
        </div>
      );
    case "error":
      return (
        <p className="mt-2 text-xs leading-relaxed text-[color:var(--fail)]" role="alert">
          {status.message}
        </p>
      );
  }
}
