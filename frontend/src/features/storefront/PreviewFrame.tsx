"use client";

import { useState, type ReactNode } from "react";
import { cx } from "@/components/ui";
import { useCart } from "./cart";
import { Storefront, type RenderLink, type StoreLike, type StoreView } from "./Storefront";

type Device = "desktop" | "phone";

/**
 * Renders the storefront inside the app with its own navigation state, so the
 * preview can be clicked through without leaving the page. The cart is in memory.
 */
export function PreviewFrame({ store, caption, highlightProductId, focusSlug, toolbarExtra }: {
  store: StoreLike;
  caption?: ReactNode;
  highlightProductId?: string | null;
  /** When set, the preview opens that product page (used while editing a product). */
  focusSlug?: string | null;
  toolbarExtra?: ReactNode;
}) {
  const [device, setDevice] = useState<Device>("desktop");
  const [view, setView] = useState<StoreView>({ kind: "home" });
  const cart = useCart(`preview:${store.id}`, false);
  const shown: StoreView = focusSlug ? { kind: "product", slug: focusSlug } : view;

  const link: RenderLink = (to, children, className, label) => (
    <button type="button" onClick={() => setView(to)} aria-label={label}
      className={cx("cursor-pointer text-left", className)}>
      {children}
    </button>
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-rule px-4 py-2">
        <div className="flex min-w-0 items-center gap-3 text-xs text-ink-2">
          {caption}
        </div>
        <div className="flex items-center gap-3">
          {toolbarExtra}
          <div role="group" aria-label="Preview width" className="flex rounded-sm border border-rule-strong text-xs">
            {(["desktop", "phone"] as const).map((d) => (
              <button key={d} type="button" aria-pressed={device === d} onClick={() => setDevice(d)}
                className={cx("h-7 px-2.5 capitalize first:rounded-l-[3px] last:rounded-r-[3px]",
                  device === d ? "bg-ink text-paper" : "text-ink-2 hover:text-ink")}>
                {d}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto bg-panel p-3 sm:p-5">
        <div className={cx("mx-auto overflow-hidden border border-rule bg-sheet shadow-[var(--shadow-sheet)] transition-[max-width] duration-300",
          device === "phone" ? "max-w-[390px] rounded-[18px]" : "max-w-none rounded-sm")}>
          {focusSlug && (
            <div className="flex items-center justify-between bg-ink px-3 py-1.5 text-xs text-paper">
              <span>Showing the product you&apos;re editing</span>
            </div>
          )}
          <Storefront store={store} view={shown} link={link} cart={cart} highlightProductId={highlightProductId}
            testNotice="Preview. Nothing here is published." />
        </div>
      </div>
    </div>
  );
}
