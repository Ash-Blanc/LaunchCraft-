"use client";

import Link from "next/link";
import type { Store } from "@/types/api";
import { useCart } from "./cart";
import { Storefront, type RenderLink, type StoreView } from "./Storefront";

export function storeHref(storeId: string, to: StoreView): string {
  const base = `/store/${encodeURIComponent(storeId)}`;
  if (to.kind === "product") return `${base}/p/${encodeURIComponent(to.slug)}`;
  if (to.kind === "cart") return `${base}/cart`;
  return base;
}

export function LiveStorefront({ store, view }: { store: Store; view: StoreView }) {
  const cart = useCart(store.id);
  const link: RenderLink = (to, children, className, label) => (
    <Link href={storeHref(store.id, to)} className={className} aria-label={label}>{children}</Link>
  );
  return (
    <Storefront store={store} view={view} link={link} cart={cart}
      testNotice="Test store: payments are not live." />
  );
}
