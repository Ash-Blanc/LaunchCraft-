"use client";

import { useCallback, useState, useSyncExternalStore } from "react";

export interface CartLine {
  productId: string;
  quantity: number;
}

export const MAX_QTY = 99;
const EMPTY: CartLine[] = [];
const CHANGE_EVENT = "launchcraft:cart-change";

function key(storeId: string) {
  return `launchcraft:cart:${storeId}`;
}

// Snapshots are cached per raw string so useSyncExternalStore sees stable references.
const cache = new Map<string, { raw: string | null; lines: CartLine[] }>();

function parse(raw: string | null): CartLine[] {
  if (!raw) return EMPTY;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return EMPTY;
    return parsed
      .filter((l): l is CartLine =>
        typeof l?.productId === "string" && Number.isInteger(l?.quantity) && l.quantity > 0)
      .map((l) => ({ productId: l.productId, quantity: Math.min(l.quantity, MAX_QTY) }));
  } catch {
    return EMPTY;
  }
}

function snapshot(storeId: string): CartLine[] {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(key(storeId));
  } catch {
    raw = null;
  }
  const hit = cache.get(storeId);
  if (hit && hit.raw === raw) return hit.lines;
  const lines = parse(raw);
  cache.set(storeId, { raw, lines });
  return lines;
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(CHANGE_EVENT, callback);
  };
}

function write(storeId: string, lines: CartLine[]) {
  try {
    window.localStorage.setItem(key(storeId), JSON.stringify(lines));
  } catch {
    /* storage unavailable; nothing persists */
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

/**
 * Cart contents only: product IDs and quantities. Prices are never stored here;
 * they're read from the store for display and computed by the server at checkout.
 * With persist=false the cart lives in memory (used by the workspace preview).
 */
export function useCart(storeId: string, persist = true) {
  const stored = useSyncExternalStore(
    subscribe,
    () => snapshot(storeId),
    () => EMPTY,
  );
  const hydrated = useSyncExternalStore(subscribe, () => true, () => false);
  const [memory, setMemory] = useState<CartLine[]>(EMPTY);
  const lines = persist ? stored : memory;

  const commit = useCallback((next: CartLine[]) => {
    if (persist) write(storeId, next);
    else setMemory(next);
  }, [persist, storeId]);

  const add = useCallback((productId: string, quantity = 1) => {
    const existing = lines.find((l) => l.productId === productId);
    commit(existing
      ? lines.map((l) => l.productId === productId ? { ...l, quantity: Math.min(l.quantity + quantity, MAX_QTY) } : l)
      : [...lines, { productId, quantity: Math.min(quantity, MAX_QTY) }]);
  }, [lines, commit]);

  const setQuantity = useCallback((productId: string, quantity: number) => {
    if (quantity <= 0) commit(lines.filter((l) => l.productId !== productId));
    else commit(lines.map((l) => l.productId === productId ? { ...l, quantity: Math.min(quantity, MAX_QTY) } : l));
  }, [lines, commit]);

  const remove = useCallback((productId: string) => commit(lines.filter((l) => l.productId !== productId)), [lines, commit]);
  const clear = useCallback(() => commit(EMPTY), [commit]);

  const count = lines.reduce((n, l) => n + l.quantity, 0);
  return { lines, loaded: persist ? hydrated : true, add, setQuantity, remove, clear, count };
}

export type Cart = ReturnType<typeof useCart>;
