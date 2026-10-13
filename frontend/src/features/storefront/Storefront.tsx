"use client";

import type { ReactNode } from "react";
import { cx } from "@/components/ui";
import { estimateSubtotal, formatPrice } from "@/lib/money";
import type { Brand, ProductInput } from "@/types/api";
import type { Cart } from "./cart";
import { MAX_QTY } from "./cart";
import { THEMES, themeVars } from "./theme";

export interface StoreProduct extends ProductInput {
  id: string;
}

export interface StoreLike {
  id: string;
  name: string;
  currency: string;
  brand: Brand;
  products: StoreProduct[];
}

export type StoreView = { kind: "home" } | { kind: "product"; slug: string } | { kind: "cart" };

export type RenderLink = (to: StoreView, children: ReactNode, className?: string, label?: string) => ReactNode;

interface Props {
  store: StoreLike;
  view: StoreView;
  link: RenderLink;
  cart: Cart;
  /** Shown in the footer and cart so nobody mistakes a test store for a live one. */
  testNotice?: string;
  highlightProductId?: string | null;
}

export function Storefront({ store, view, link, cart, testNotice, highlightProductId }: Props) {
  const theme = THEMES[store.brand.visual_direction] ?? THEMES.editorial;
  return (
    <div
      style={{ ...themeVars(store.brand), fontFamily: "var(--s-body)" }}
      className="@container flex min-h-full flex-1 flex-col bg-[color:var(--s-surface)] text-[color:var(--s-ink)]"
    >
      <StoreHeader store={store} link={link} count={cart.count} />
      <main className="flex-1">
        {view.kind === "home" && <Home store={store} link={link} cart={cart} highlight={highlightProductId} />}
        {view.kind === "product" && <ProductPage store={store} slug={view.slug} link={link} cart={cart} />}
        {view.kind === "cart" && <CartPage store={store} link={link} cart={cart} />}
      </main>
      <footer className="mt-16 border-t border-[color:var(--s-rule)] px-5 py-6 text-xs text-[color:var(--s-muted)] @3xl:px-10">
        <div className="flex flex-col gap-1 @md:flex-row @md:justify-between">
          <span>© {store.name}. Prices in {store.currency}.</span>
          {testNotice && <span>{testNotice}</span>}
        </div>
      </footer>
      <span className="sr-only">{theme.label}</span>
    </div>
  );
}

function Display({ as: Tag = "h1", className, children }: { as?: "h1" | "h2" | "h3"; className?: string; children: ReactNode }) {
  return (
    <Tag className={cx("text-balance", className)}
      style={{ fontFamily: "var(--s-display)", fontWeight: "var(--s-heading-weight)", letterSpacing: "-0.015em" }}>
      {children}
    </Tag>
  );
}

function StoreHeader({ store, link, count }: { store: StoreLike; link: RenderLink; count: number }) {
  const d = store.brand.visual_direction;
  return (
    <header className={cx(
      "flex items-center justify-between gap-4 px-5 py-4 @3xl:px-10",
      d === "workshop" ? "border-b-2 border-[color:var(--s-ink)]" : "border-b border-[color:var(--s-rule)]",
      d === "botanical" && "justify-center @md:justify-between",
    )}>
      {link({ kind: "home" }, (
        <span style={{ fontFamily: "var(--s-display)", fontWeight: "var(--s-heading-weight)" }}
          className={cx("text-lg leading-tight @md:text-xl", d === "workshop" && "uppercase tracking-tight")}>
          {store.name}
        </span>
      ), "min-w-0 truncate", `${store.name} home`)}
      <nav aria-label="Store" className="flex shrink-0 items-center gap-5 text-sm">
        {link({ kind: "home" }, "Shop", "hidden hover:underline underline-offset-4 @md:inline")}
        {link({ kind: "cart" }, (
          <span className="inline-flex items-center gap-1.5">
            Cart
            <span className="tabular inline-flex min-w-5 justify-center rounded-full bg-[color:var(--s-accent)] px-1.5 text-xs leading-5 text-[color:var(--s-on-accent)]">
              {count}
            </span>
          </span>
        ), "hover:underline underline-offset-4", `Cart, ${count} item${count === 1 ? "" : "s"}`)}
      </nav>
    </header>
  );
}

function ProductImage({ product, className, sizes = "card" }: { product: StoreProduct; className?: string; sizes?: "card" | "large" | "thumb" }) {
  if (!product.image_url) {
    return (
      <div className={cx("flex items-center justify-center bg-[color:var(--s-raised)] text-[color:var(--s-muted)]", className)}
        role="img" aria-label={`${product.name} (no image yet)`}>
        <span style={{ fontFamily: "var(--s-display)" }} className={sizes === "thumb" ? "text-lg" : "text-5xl"}>
          {product.name.slice(0, 1)}
        </span>
      </div>
    );
  }
  return (
    // Plain <img>: product images may come from any https host the merchant chooses.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={product.image_url} alt={product.image_alt || product.name} loading="lazy" referrerPolicy="no-referrer"
      className={cx("bg-[color:var(--s-raised)] object-cover", className)} />
  );
}

function Price({ product, currency, className }: { product: StoreProduct; currency: string; className?: string }) {
  return <span className={cx("tabular", className)}>{formatPrice(product.price, currency)}</span>;
}

// --- Home -------------------------------------------------------------------------------
function Home({ store, link, cart, highlight }: { store: StoreLike; link: RenderLink; cart: Cart; highlight?: string | null }) {
  const products = store.products;
  const theme = THEMES[store.brand.visual_direction] ?? THEMES.editorial;
  const lead = products.find((p) => p.available && p.image_url) ?? products[0];

  return (
    <>
      <Hero store={store} lead={lead} link={link} />
      <section aria-labelledby="shop-heading" className="px-5 pt-12 @3xl:px-10">
        <Display as="h2" className="mb-6 text-2xl">
          <span id="shop-heading">{store.brand.visual_direction === "minimal" ? "Everything" : "The range"}</span>
        </Display>
        {products.length === 0 ? (
          <div className="border border-dashed border-[color:var(--s-rule)] px-6 py-14 text-center">
            <p className="text-sm text-[color:var(--s-muted)]">Nothing for sale yet. Products you add will appear here.</p>
          </div>
        ) : (
          <ul className={theme.grid}>
            {products.map((p) => (
              <li key={p.id} className={cx(theme.card, highlight === p.id && "outline-2 outline-offset-4 outline-[color:var(--s-accent)]")}>
                {store.brand.visual_direction === "minimal"
                  ? <ListRow store={store} product={p} link={link} cart={cart} />
                  : <ProductCard store={store} product={p} link={link} />}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

function Hero({ store, lead, link }: { store: StoreLike; lead?: StoreProduct; link: RenderLink }) {
  const { brand } = store;
  const tagline = brand.tagline || "A small shop, just getting started.";
  switch (THEMES[brand.visual_direction]?.hero ?? "split") {
    case "arch":
      return (
        <section className="flex flex-col items-center px-5 pt-12 text-center">
          <Display className="max-w-[18ch] text-4xl leading-[1.05] @3xl:text-6xl">{store.name}</Display>
          <p className="mt-4 max-w-[46ch] text-base text-[color:var(--s-muted)]">{tagline}</p>
          {lead && (
            <div className="mt-10 w-full max-w-xs @md:max-w-sm">
              <ProductImage product={lead} className="aspect-[4/5] w-full rounded-t-[999px]" />
            </div>
          )}
        </section>
      );
    case "block":
      return (
        <section className="bg-[color:var(--s-accent)] px-5 py-12 text-[color:var(--s-on-accent)] @3xl:px-10 @3xl:py-20">
          <Display className="max-w-[14ch] text-5xl uppercase leading-[0.92] @3xl:text-8xl">{store.name}</Display>
          <p className="mt-6 max-w-[44ch] text-base opacity-90">{tagline}</p>
        </section>
      );
    case "sticker":
      return (
        <section className="relative px-5 pt-10 @3xl:px-10">
          <div className="rounded-[32px] bg-[color:var(--s-accent)] px-6 py-12 text-[color:var(--s-on-accent)] @3xl:px-12 @3xl:py-16">
            <Display className="max-w-[16ch] text-4xl leading-[1.02] @3xl:text-6xl">{store.name}</Display>
            <p className="mt-4 max-w-[40ch] text-base opacity-90">{tagline}</p>
          </div>
          {lead && (
            <span className="absolute -bottom-3 right-8 -rotate-6 rounded-full bg-[color:var(--s-ink)] px-4 py-2 text-sm text-[color:var(--s-surface)] shadow-lg">
              from <Price product={lead} currency={store.currency} />
            </span>
          )}
        </section>
      );
    case "quiet":
      return (
        <section className="px-5 pb-4 pt-16 @3xl:px-10 @3xl:pt-24">
          <Display className="max-w-[20ch] text-4xl leading-tight @3xl:text-5xl">{store.name}</Display>
          <p className="mt-3 max-w-[50ch] text-[color:var(--s-muted)]">{tagline}</p>
        </section>
      );
    default:
      return (
        <section className="grid grid-cols-1 items-end gap-8 px-5 pt-10 @3xl:grid-cols-[1.15fr_0.85fr] @3xl:px-10 @3xl:pt-14">
          <div>
            <Display className="max-w-[12ch] text-5xl leading-[0.98] @3xl:text-7xl">{store.name}</Display>
            <p className="mt-6 max-w-[38ch] text-lg leading-relaxed text-[color:var(--s-muted)]"
              style={{ fontFamily: "var(--s-display)", fontStyle: "italic" }}>
              {tagline}
            </p>
          </div>
          {lead && link({ kind: "product", slug: lead.slug }, (
            <figure>
              <ProductImage product={lead} className="aspect-[4/5] w-full" />
              <figcaption className="mt-2 flex justify-between text-sm">
                <span>{lead.name}</span>
                <Price product={lead} currency={store.currency} className="text-[color:var(--s-muted)]" />
              </figcaption>
            </figure>
          ), "block", lead.name)}
        </section>
      );
  }
}

function ProductCard({ store, product, link }: { store: StoreLike; product: StoreProduct; link: RenderLink }) {
  const theme = THEMES[store.brand.visual_direction] ?? THEMES.editorial;
  const playful = store.brand.visual_direction === "playful";
  return link({ kind: "product", slug: product.slug }, (
    <article className="group">
      <div className="relative">
        <ProductImage product={product} className={cx("w-full", theme.imageAspect, theme.imageFrame)} />
        {playful && (
          <span className="absolute left-3 top-3 -rotate-3 rounded-full bg-[color:var(--s-accent)] px-3 py-1 text-sm font-medium text-[color:var(--s-on-accent)]">
            <Price product={product} currency={store.currency} />
          </span>
        )}
        {!product.available && (
          <span className="absolute bottom-3 left-3 bg-[color:var(--s-surface)] px-2 py-1 text-xs">Sold out</span>
        )}
      </div>
      <div className={cx("mt-3 flex",
        theme.card.includes("text-center") ? "flex-col items-center gap-1"
          : store.brand.visual_direction === "workshop" ? "flex-col gap-1" : "items-baseline justify-between gap-3")}>
        <Display as="h3" className={cx("text-lg leading-snug group-hover:underline group-hover:underline-offset-4",
          store.brand.visual_direction === "workshop" && "text-base")}>
          {product.name}
        </Display>
        {!playful && <Price product={product} currency={store.currency} className="shrink-0 text-sm text-[color:var(--s-muted)]" />}
      </div>
    </article>
  ), "block", product.name);
}

function ListRow({ store, product, link, cart }: { store: StoreLike; product: StoreProduct; link: RenderLink; cart: Cart }) {
  return (
    <div className="flex items-center gap-4 py-4">
      <ProductImage product={product} className="size-16 shrink-0 @md:size-20" sizes="thumb" />
      <div className="min-w-0 flex-1">
        {link({ kind: "product", slug: product.slug }, (
          <span className="text-base hover:underline underline-offset-4">{product.name}</span>
        ), undefined, product.name)}
        <p className="truncate text-sm text-[color:var(--s-muted)]">{product.description}</p>
      </div>
      <Price product={product} currency={store.currency} className="text-sm" />
      <button type="button" disabled={!product.available} onClick={() => cart.add(product.id)}
        className="hidden h-9 border border-[color:var(--s-ink)] px-3 text-sm disabled:opacity-40 @md:block">
        {product.available ? "Add" : "Sold out"}
      </button>
    </div>
  );
}

// --- Product page -----------------------------------------------------------------------
function ProductPage({ store, slug, link, cart }: { store: StoreLike; slug: string; link: RenderLink; cart: Cart }) {
  const product = store.products.find((p) => p.slug === slug);
  const theme = THEMES[store.brand.visual_direction] ?? THEMES.editorial;
  if (!product) {
    return (
      <div className="px-5 py-20 text-center">
        <Display as="h1" className="text-3xl">This product isn&apos;t here</Display>
        <p className="mt-2 text-sm text-[color:var(--s-muted)]">It may have been removed or renamed.</p>
        <div className="mt-6">{link({ kind: "home" }, "Back to the shop", "underline underline-offset-4")}</div>
      </div>
    );
  }
  const inCart = cart.lines.find((l) => l.productId === product.id)?.quantity ?? 0;
  return (
    <article className="grid grid-cols-1 gap-8 px-5 pt-8 @3xl:grid-cols-2 @3xl:gap-14 @3xl:px-10 @3xl:pt-12">
      <ProductImage product={product} sizes="large" className={cx("w-full", theme.imageAspect, theme.imageFrame)} />
      <div className="flex flex-col @3xl:pt-6">
        <div className="text-sm">{link({ kind: "home" }, `${store.name}`, "text-[color:var(--s-muted)] hover:underline underline-offset-4")}</div>
        <Display className="mt-3 text-4xl leading-[1.06] @3xl:text-5xl">{product.name}</Display>
        <Price product={product} currency={store.currency} className="mt-3 text-xl" />
        <p className="mt-6 max-w-[58ch] whitespace-pre-line text-base leading-relaxed">{product.description}</p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button type="button" disabled={!product.available || inCart >= MAX_QTY}
            onClick={() => cart.add(product.id)}
            className={cx("h-12 px-6 text-sm font-medium disabled:opacity-40",
              store.brand.visual_direction === "playful" || store.brand.visual_direction === "botanical" ? "rounded-full" : "",
              "bg-[color:var(--s-accent)] text-[color:var(--s-on-accent)]")}>
            {product.available ? "Add to cart" : "Sold out"}
          </button>
          {inCart > 0 && (
            <span className="text-sm text-[color:var(--s-muted)]" role="status">
              {inCart} in your cart. {link({ kind: "cart" }, "View cart", "underline underline-offset-4")}
            </span>
          )}
        </div>
        {product.inventory != null && product.available && product.inventory <= 5 && (
          <p className="mt-3 text-sm text-[color:var(--s-muted)]">Only {product.inventory} left.</p>
        )}
      </div>
    </article>
  );
}

// --- Cart -------------------------------------------------------------------------------
function CartPage({ store, link, cart }: { store: StoreLike; link: RenderLink; cart: Cart }) {
  const byId = new Map(store.products.map((p) => [p.id, p]));
  const lines = cart.lines.map((l) => ({ ...l, product: byId.get(l.productId) }));
  const valid = lines.filter((l) => l.product && l.product.available);
  const problems = lines.filter((l) => !l.product || !l.product.available);
  const subtotal = estimateSubtotal(valid.map((l) => ({ price: l.product!.price, quantity: l.quantity })), store.currency);

  return (
    <section className="px-5 pt-10 @3xl:px-10">
      <Display className="text-4xl">Your cart</Display>
      {!cart.loaded ? (
        <div className="mt-8 h-24 skeleton" aria-label="Loading cart" />
      ) : lines.length === 0 ? (
        <div className="mt-8 max-w-md">
          <p className="text-[color:var(--s-muted)]">Your cart is empty.</p>
          <div className="mt-4">{link({ kind: "home" }, "Browse the range", "underline underline-offset-4")}</div>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-10 @3xl:grid-cols-[1fr_20rem]">
          <ul className="divide-y divide-[color:var(--s-rule)] border-y border-[color:var(--s-rule)]">
            {lines.map(({ productId, quantity, product }) => (
              <li key={productId} className="flex items-center gap-4 py-4">
                {product ? <ProductImage product={product} sizes="thumb" className="size-16 shrink-0" /> : <div className="size-16 shrink-0 bg-[color:var(--s-raised)]" />}
                <div className="min-w-0 flex-1">
                  <p className="truncate">{product?.name ?? "Removed product"}</p>
                  {product && !product.available && <p className="text-sm text-[color:var(--s-muted)]">Sold out. Remove it to check out.</p>}
                  {!product && <p className="text-sm text-[color:var(--s-muted)]">No longer sold here.</p>}
                </div>
                {product?.available && (
                  <label className="flex items-center gap-2 text-sm">
                    <span className="sr-only">Quantity of {product.name}</span>
                    <select value={quantity} onChange={(e) => cart.setQuantity(productId, Number(e.target.value))}
                      className="h-9 border border-[color:var(--s-rule)] bg-transparent px-2 tabular">
                      {Array.from({ length: Math.max(10, quantity) }, (_, i) => i + 1).map((n) => <option key={n} value={n}>{n}</option>)}
                    </select>
                  </label>
                )}
                {product?.available && <Price product={product} currency={store.currency} className="w-20 text-right text-sm" />}
                <button type="button" onClick={() => cart.remove(productId)} className="text-sm underline underline-offset-4"
                  aria-label={`Remove ${product?.name ?? "item"}`}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <aside className="h-fit border border-[color:var(--s-rule)] p-5">
            <div className="flex items-baseline justify-between">
              <span>Estimated subtotal</span>
              <span className="tabular text-lg">{formatPrice(subtotal, store.currency)}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-[color:var(--s-muted)]">
              The final total is calculated by the store&apos;s server from current prices when you check out.
            </p>
            <button type="button" disabled
              className="mt-5 h-12 w-full cursor-not-allowed bg-[color:var(--s-ink)] text-sm font-medium text-[color:var(--s-surface)] opacity-45"
              aria-describedby="checkout-unavailable">
              Check out with PayPal
            </button>
            <p id="checkout-unavailable" className="mt-2 text-xs leading-relaxed text-[color:var(--s-muted)]">
              Checkout isn&apos;t connected yet. PayPal Sandbox payments arrive in the next build phase; your cart is kept until then.
            </p>
            {problems.length > 0 && (
              <p className="mt-3 text-xs text-[color:var(--s-muted)]">
                {problems.length} item{problems.length === 1 ? " needs" : "s need"} attention before checkout.
              </p>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
