"use client";

import { useState, type FormEvent } from "react";
import { Button, Notice, TextField, cx } from "@/components/ui";
import { THEMES, contrast } from "@/features/storefront/theme";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { Brand, Store, VisualDirection } from "@/types/api";

const HEX = /^#[0-9a-fA-F]{6}$/;
const DIRECTIONS = Object.keys(THEMES) as VisualDirection[];

interface BrandDraft { name: string; brand: Brand }

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function BrandEditor({ store, onDraft, onSaved }: {
  store: Store;
  onDraft: (d: BrandDraft | null) => void;
  onSaved: (message: string) => void;
}) {
  const [draft, setDraft] = useState<BrandDraft>({ name: store.name, brand: store.brand });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const dirty = draft.name !== store.name || JSON.stringify(draft.brand) !== JSON.stringify(store.brand);
  const colorsValid = HEX.test(draft.brand.accent_color) && HEX.test(draft.brand.ink_color) && HEX.test(draft.brand.surface_color);
  const textContrast = colorsValid ? contrast(draft.brand.ink_color, draft.brand.surface_color) : 0;

  const set = (patch: Partial<BrandDraft> | { brand: Partial<Brand> }) => {
    const next: BrandDraft = {
      name: "name" in patch && patch.name !== undefined ? patch.name : draft.name,
      brand: "brand" in patch && patch.brand ? { ...draft.brand, ...patch.brand } : draft.brand,
    };
    setDraft(next);
    const previewable = HEX.test(next.brand.accent_color) && HEX.test(next.brand.ink_color) && HEX.test(next.brand.surface_color);
    onDraft(previewable ? next : null);
  };

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!draft.name.trim()) { setFieldErrors({ name: "The store needs a name." }); return; }
    if (!colorsValid) { setFieldErrors({ accent_color: "Colours must be hex values like #2A45C2." }); return; }
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      await api.patchStore(store.id, { name: draft.name.trim(), brand: draft.brand });
      setBusy(false);
      onSaved("Brand saved");
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError) setFieldErrors(err.fields);
      setError(errorMessage(err));
    }
  }

  function reset() {
    setDraft({ name: store.name, brand: store.brand });
    onDraft(null);
    setFieldErrors({});
    setError(null);
  }

  return (
    <form onSubmit={save} noValidate className="flex flex-col gap-7">
      <h2 className="font-display text-2xl">Brand</h2>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <TextField label="Store name" value={draft.name} maxLength={80} error={fieldErrors.name}
          onChange={(e) => set({ name: e.target.value })} />
        <TextField label="Tagline" optional value={draft.brand.tagline} maxLength={120} error={fieldErrors.tagline}
          onChange={(e) => set({ brand: { tagline: e.target.value } })} />
      </div>

      <fieldset>
        <legend className="text-sm font-medium">Look</legend>
        <div className="mt-2 grid grid-cols-1 gap-px overflow-hidden rounded-sm border border-rule-strong bg-rule-strong sm:grid-cols-2">
          {DIRECTIONS.map((d) => {
            const selected = draft.brand.visual_direction === d;
            return (
              <label key={d} className={cx("flex cursor-pointer flex-col gap-0.5 px-4 py-3 has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2 has-[:focus-visible]:outline-stamp",
                selected ? "bg-stamp-wash" : "bg-sheet hover:bg-paper")}>
                <input type="radio" name="look" className="sr-only" checked={selected}
                  onChange={() => set({ brand: { visual_direction: d } })} />
                <span className="text-lg capitalize leading-tight"
                  style={{ fontFamily: THEMES[d].display, fontWeight: THEMES[d].headingWeight }}>{d}</span>
                <span className="text-xs text-ink-2">{capitalize(THEMES[d].label.split(": ")[1])}</span>
              </label>
            );
          })}
          {DIRECTIONS.length % 2 === 1 && <div aria-hidden className="hidden bg-sheet sm:block" />}
        </div>
      </fieldset>

      <fieldset className="grid grid-cols-[repeat(auto-fill,minmax(11.5rem,1fr))] gap-4">
        <legend className="mb-2 text-sm font-medium">Colours</legend>
        {([["accent_color", "Accent"], ["ink_color", "Text"], ["surface_color", "Background"]] as const).map(([k, label]) => (
          <div key={k} className="flex items-end gap-2">
            <input type="color" aria-label={`${label} colour picker`}
              value={HEX.test(draft.brand[k]) ? draft.brand[k] : "#000000"}
              onChange={(e) => set({ brand: { [k]: e.target.value.toUpperCase() } })}
              className="h-10 w-11 shrink-0 cursor-pointer rounded-sm border border-rule-strong bg-sheet p-1" />
            <TextField label={label} value={draft.brand[k]} maxLength={7} className="min-w-0 flex-1 tabular"
              error={fieldErrors[k]} onChange={(e) => set({ brand: { [k]: e.target.value } })} />
          </div>
        ))}
      </fieldset>
      {colorsValid && textContrast < 4.5 && (
        <Notice tone="warn" title="Text may be hard to read">
          Text on the background has a contrast ratio of {textContrast.toFixed(1)}:1. Aim for at least 4.5:1.
        </Notice>
      )}

      {error && <Notice tone="error" title="The brand wasn't saved">{error}</Notice>}
      <div className="flex items-center gap-3 border-t border-rule pt-5">
        <Button type="submit" busy={busy} disabled={!dirty}>Save brand</Button>
        <Button type="button" variant="secondary" onClick={reset} disabled={!dirty || busy}>Discard changes</Button>
        {!dirty && <span className="text-xs text-ink-2">No unsaved changes</span>}
      </div>
    </form>
  );
}
