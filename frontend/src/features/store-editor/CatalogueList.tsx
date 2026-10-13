"use client";

import { Button, cx } from "@/components/ui";
import { formatPrice } from "@/lib/money";
import type { Product } from "@/types/api";

export function CatalogueList({ products, currency, onEdit, onAdd, highlightId }: {
  products: Product[];
  currency: string;
  onEdit: (p: Product) => void;
  onAdd: () => void;
  highlightId?: string | null;
}) {
  const live = products.filter((p) => p.available).length;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl">Catalogue</h2>
          <p className="tabular text-sm text-ink-2">
            {products.length} product{products.length === 1 ? "" : "s"}, {live} for sale
          </p>
        </div>
        <Button onClick={onAdd}>Add product</Button>
      </div>

      {products.length === 0 ? (
        <div className="rounded-sm border border-dashed border-rule-strong px-6 py-12 text-center">
          <p className="font-display text-xl">No products yet</p>
          <p className="mx-auto mt-2 max-w-[36ch] text-sm text-ink-2">
            Add one yourself, or ask the assistant to suggest a product from the sample range.
          </p>
          <Button className="mt-5" onClick={onAdd}>Add your first product</Button>
        </div>
      ) : (
        <ul className="divide-y divide-rule border-y border-rule">
          {products.map((p) => {
            const gaps = [
              p.description.length < 40 && "short description",
              !p.image_url && "no image",
              p.image_url && !p.image_alt && "no image description",
            ].filter(Boolean) as string[];
            return (
              <li key={p.id}>
                <button type="button" onClick={() => onEdit(p)}
                  className={cx("group grid w-full grid-cols-[3.5rem_1fr_auto] items-center gap-4 py-3 text-left transition-colors hover:bg-sheet",
                    highlightId === p.id && "bg-stamp-wash")}>
                  {p.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.image_url} alt="" className="size-14 bg-panel object-cover" />
                  ) : (
                    <span className="flex size-14 items-center justify-center bg-panel font-display text-xl text-ink-3">{p.name.slice(0, 1)}</span>
                  )}
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium group-hover:underline group-hover:underline-offset-4">{p.name}</span>
                    <span className="block truncate text-xs text-ink-2">
                      {!p.available ? "Sold out" : p.inventory != null ? `${p.inventory} in stock` : "For sale"}
                      {gaps.length > 0 && <span className="text-wait">, {gaps.join(", ")}</span>}
                    </span>
                  </span>
                  <span className="tabular pr-1 text-sm">{formatPrice(p.price, currency)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
