"use client";

import { useState, type FormEvent } from "react";
import { Button, ConfirmDialog, Notice, TextArea, TextField, cx } from "@/components/ui";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { Product, ProductInput } from "@/types/api";
import { IMAGE_LIBRARY } from "./imageLibrary";
import { slugify, validateProduct } from "./validation";

function toInput(p: Product): ProductInput {
  return {
    slug: p.slug, name: p.name, description: p.description, price: p.price, currency: p.currency,
    image_url: p.image_url, image_alt: p.image_alt, available: p.available, inventory: p.inventory,
  };
}

export function ProductForm({ storeId, currency, product, takenSlugs, onDraft, onDone }: {
  storeId: string;
  currency: string;
  product: Product | null;
  takenSlugs: string[];
  onDraft: (draft: ProductInput) => void;
  onDone: (message: string) => void;
}) {
  const isNew = product === null;
  const [form, setForm] = useState<ProductInput>(product ? toInput(product) : {
    slug: "", name: "", description: "", price: "", currency, image_url: "", image_alt: "", available: true, inventory: null,
  });
  const [slugTouched, setSlugTouched] = useState(!isNew);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showErrors, setShowErrors] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [imageMode, setImageMode] = useState<"library" | "url">(
    form.image_url.startsWith("https://") ? "url" : "library");

  const update = (patch: Partial<ProductInput>) => {
    const next = { ...form, ...patch };
    if ("name" in patch && !slugTouched) next.slug = slugify(patch.name ?? "");
    setForm(next);
    onDraft(next);
    if (showErrors) setErrors(validateProduct(next, takenSlugs));
  };

  async function save(e: FormEvent) {
    e.preventDefault();
    const found = validateProduct(form, takenSlugs);
    setErrors(found);
    setShowErrors(true);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFormError(null);
    const payload = { ...form, price: form.price.trim(), image_url: form.image_url.trim() };
    try {
      if (isNew) await api.addProduct(storeId, payload);
      else await api.updateProduct(storeId, product.id, payload);
      onDone(isNew ? `Added ${payload.name}` : `Saved ${payload.name}`);
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError) {
        const { _: general, ...fields } = err.fields;
        if (Object.keys(fields).length) setErrors(fields);
        setFormError(general ?? (Object.keys(fields).length ? "Some fields need attention." : err.message));
      } else {
        setFormError(errorMessage(err));
      }
    }
  }

  async function remove() {
    if (!product) return;
    setDeleting(true);
    try {
      await api.deleteProduct(storeId, product.id);
      setConfirmDelete(false);
      onDone(`Removed ${product.name}`);
    } catch (err) {
      setDeleting(false);
      setConfirmDelete(false);
      setFormError(errorMessage(err));
    }
  }

  return (
    <form onSubmit={save} noValidate className="flex flex-col gap-6" aria-label={isNew ? "New product" : `Edit ${product.name}`}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl">{isNew ? "New product" : "Edit product"}</h2>
        <Button type="button" variant="quiet" className="text-sm" onClick={() => onDone("")}>Cancel</Button>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-[1fr_10rem]">
        <TextField label="Name" value={form.name} maxLength={80} onChange={(e) => update({ name: e.target.value })}
          error={errors.name} autoFocus={isNew} />
        <TextField label={`Price (${currency})`} value={form.price} inputMode="decimal" maxLength={12}
          onChange={(e) => update({ price: e.target.value })} error={errors.price} className="tabular" />
      </div>

      <TextArea label="Description" value={form.description} maxLength={1200} rows={4}
        onChange={(e) => update({ description: e.target.value })} error={errors.description}
        hint={`${form.description.length}/1200. Launch checks ask for at least 40 characters: materials, size, care.`} />

      <fieldset>
        <legend className="text-sm font-medium">Image</legend>
        <div role="tablist" aria-label="Image source" className="mt-2 flex gap-4 text-sm">
          {(["library", "url"] as const).map((m) => (
            <button key={m} type="button" role="tab" aria-selected={imageMode === m} onClick={() => setImageMode(m)}
              className={cx("border-b-2 pb-1", imageMode === m ? "border-ink font-medium" : "border-transparent text-ink-2")}>
              {m === "library" ? "Illustration library" : "Image address"}
            </button>
          ))}
        </div>
        {imageMode === "library" ? (
          <div className="mt-3">
            <div className="grid grid-cols-5 gap-2 sm:grid-cols-7">
              <button type="button" onClick={() => update({ image_url: "" })} aria-pressed={!form.image_url}
                className={cx("flex aspect-square items-center justify-center border text-[11px] text-ink-2",
                  !form.image_url ? "border-stamp ring-2 ring-stamp/30" : "border-rule hover:border-ink")}>
                None
              </button>
              {IMAGE_LIBRARY.map((img) => (
                <button key={img.url} type="button" title={img.label} aria-label={img.label}
                  aria-pressed={form.image_url === img.url}
                  onClick={() => update({ image_url: img.url, image_alt: form.image_alt || img.label })}
                  className={cx("aspect-square overflow-hidden border",
                    form.image_url === img.url ? "border-stamp ring-2 ring-stamp/30" : "border-rule hover:border-ink")}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img.url} alt="" className="size-full object-cover" />
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-ink-2">Illustrations made for this demo. Replace them with real product photos before launch.</p>
          </div>
        ) : (
          <TextField className="mt-3" label="Image address" placeholder="https://…" value={form.image_url} maxLength={500}
            onChange={(e) => update({ image_url: e.target.value })} error={errors.image_url}
            hint="Must start with https://. The image is shown as-is from that address." />
        )}
        <TextField className="mt-4" label="Image description" optional value={form.image_alt} maxLength={160}
          onChange={(e) => update({ image_alt: e.target.value })}
          hint="Read aloud by screen readers. Describe what the photo shows." />
      </fieldset>

      <fieldset className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <legend className="sr-only">Availability</legend>
        <label className="flex items-start gap-3 rounded-sm border border-rule-strong bg-sheet px-3 py-2.5">
          <input type="checkbox" checked={form.available} onChange={(e) => update({ available: e.target.checked })}
            className="mt-0.5 size-4 accent-[var(--color-stamp)]" />
          <span>
            <span className="block text-sm font-medium">For sale</span>
            <span className="block text-xs text-ink-2">Unticked products show as sold out.</span>
          </span>
        </label>
        <TextField label="Stock" optional inputMode="numeric" placeholder="Not tracked"
          value={form.inventory ?? ""} error={errors.inventory}
          onChange={(e) => update({ inventory: e.target.value === "" ? null : Number(e.target.value) })} />
      </fieldset>

      <details className="text-sm" open={!!errors.slug}>
        <summary className="cursor-pointer text-ink-2">Product address</summary>
        <TextField className="mt-3" label="URL name" value={form.slug} maxLength={60} error={errors.slug}
          onChange={(e) => { setSlugTouched(true); update({ slug: e.target.value }); }}
          hint={`The product page will be at /p/${form.slug || "…"}`} />
      </details>

      {formError && <Notice tone="error" title={isNew ? "The product wasn't added" : "Changes weren't saved"}>{formError}</Notice>}

      <div className="flex flex-wrap items-center gap-3 border-t border-rule pt-5">
        <Button type="submit" busy={busy}>{isNew ? "Add product" : "Save changes"}</Button>
        <Button type="button" variant="secondary" onClick={() => onDone("")}>Cancel</Button>
        {!isNew && (
          <Button type="button" variant="quiet" className="ml-auto text-sm text-fail decoration-fail/40"
            onClick={() => setConfirmDelete(true)}>
            Remove product
          </Button>
        )}
      </div>

      {!isNew && (
        <ConfirmDialog open={confirmDelete} title={`Remove ${product.name}?`} confirmLabel="Remove product" busy={deleting}
          body="It will disappear from the storefront and any carts. Past orders keep their record."
          onConfirm={remove} onCancel={() => setConfirmDelete(false)} />
      )}
    </form>
  );
}
