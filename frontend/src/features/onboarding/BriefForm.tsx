"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button, Notice, SelectField, TextArea, TextField, cx } from "@/components/ui";
import { ShineBorder } from "@/components/ui/shine-border";
import { api, ApiError, errorMessage } from "@/lib/api";
import { CURRENCIES } from "@/lib/money";
import { THEMES } from "@/features/storefront/theme";
import type { BusinessBrief, VisualDirection } from "@/types/api";
import { EMPTY_BRIEF, EXAMPLE_BRIEFS, saveBrief } from "./examples";

const DIRECTIONS: { value: VisualDirection | "auto"; name: string; note: string }[] = [
  { value: "auto", name: "Let the assistant choose", note: "Picked to suit what you sell" },
  { value: "editorial", name: "Editorial", note: "Serif masthead, magazine grid" },
  { value: "botanical", name: "Botanical", note: "Soft serif, arched images" },
  { value: "workshop", name: "Workshop", note: "Bold type, dense catalogue" },
  { value: "playful", name: "Playful", note: "Rounded shapes, price stickers" },
  { value: "minimal", name: "Minimal", note: "One typeface, quiet list" },
];

export function BriefForm({ initial }: { initial?: BusinessBrief | null }) {
  const router = useRouter();
  const [brief, setBrief] = useState<BusinessBrief>(initial ?? EMPTY_BRIEF);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const set = <K extends keyof BusinessBrief>(k: K, v: BusinessBrief[K]) => {
    setBrief((b) => ({ ...b, [k]: v }));
    if (fieldErrors[k]) setFieldErrors((prev) => { const next = { ...prev }; delete next[k]; return next; });
  };

  function fillExample() {
    setBrief(EXAMPLE_BRIEFS[exampleIndex % EXAMPLE_BRIEFS.length]);
    setExampleIndex((i) => i + 1);
    setFieldErrors({});
    setError(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!brief.business_name.trim()) local.business_name = "Give the business a name, even a working one.";
    if (brief.niche.trim().length < 3) local.niche = "Describe what you sell in a few words.";
    if (Object.keys(local).length) {
      setFieldErrors(local);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      saveBrief(brief);
      const proposal = await api.draftStore(brief);
      router.push(`/draft/${proposal.id}`);
    } catch (err) {
      setBusy(false);
      if (err instanceof ApiError && Object.keys(err.fields).length) setFieldErrors(err.fields);
      setError(errorMessage(err));
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl">Your brief</h2>
        <Button type="button" variant="quiet" onClick={fillExample} className="text-sm">
          {exampleIndex === 0 ? "Fill in an example" : "Try another example"}
        </Button>
      </div>

      <fieldset className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <legend className="sr-only">The business</legend>
        <TextField label="Business name" placeholder="Slow Kiln" value={brief.business_name}
          onChange={(e) => set("business_name", e.target.value)} error={fieldErrors.business_name} maxLength={80} />
        <TextField label="What you sell" placeholder="Handmade stoneware mugs and bowls" value={brief.niche}
          onChange={(e) => set("niche", e.target.value)} error={fieldErrors.niche} maxLength={160} />
        <TextField label="Who buys it" optional placeholder="Home cooks who buy fewer, better things" value={brief.audience}
          onChange={(e) => set("audience", e.target.value)} error={fieldErrors.audience} maxLength={200} className="sm:col-span-2" />
        <TextField label="How it should feel" optional placeholder="Sturdy, warm, unfussy"
          hint="Used as the store's tagline in the draft." value={brief.personality}
          onChange={(e) => set("personality", e.target.value)} error={fieldErrors.personality} maxLength={200} className="sm:col-span-2" />
      </fieldset>

      <fieldset>
        <legend className="text-sm font-medium">Look</legend>
        <div className="mt-2 grid grid-cols-1 gap-px overflow-hidden rounded-sm border border-rule-strong bg-rule-strong sm:grid-cols-2 lg:grid-cols-3">
          {DIRECTIONS.map((d) => {
            const selected = brief.visual_direction === d.value;
            const font = d.value === "auto" ? "var(--font-sans)" : THEMES[d.value].display;
            return (
              <label key={d.value}
                className={cx("relative flex cursor-pointer flex-col gap-1 py-3 pl-4 pr-8 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2 has-[:focus-visible]:outline-stamp",
                  selected ? "bg-stamp-wash" : "bg-sheet hover:bg-paper")}>
                <input type="radio" name="direction" value={d.value} checked={selected}
                  onChange={() => set("visual_direction", d.value)} className="sr-only" />
                <span className="text-lg leading-tight" style={{ fontFamily: font, fontWeight: d.value === "workshop" ? 750 : d.value === "minimal" ? 300 : 400 }}>
                  {d.name}
                </span>
                <span className="text-xs text-ink-2">{d.note}</span>
                {selected && <span aria-hidden className="absolute right-3 top-3 size-2 rounded-full bg-stamp" />}
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="grid grid-cols-1 gap-5 sm:grid-cols-[1fr_1fr]">
        <legend className="sr-only">Products and pricing</legend>
        <TextArea label="Example products" optional className="sm:col-span-2"
          placeholder={"Tall latte mug - 34\nRamen bowl - 42\nButter dish"}
          hint="One per line, with a price if you know it. Leave empty to start from a sample range."
          value={brief.example_products} onChange={(e) => set("example_products", e.target.value)}
          error={fieldErrors.example_products} maxLength={1200} rows={4} />
        <div className="grid grid-cols-2 gap-3">
          <TextField label="Lowest price" optional inputMode="decimal" placeholder="15" value={brief.price_min}
            onChange={(e) => set("price_min", e.target.value)} error={fieldErrors.price_min} maxLength={12} />
          <TextField label="Highest price" optional inputMode="decimal" placeholder="70" value={brief.price_max}
            onChange={(e) => set("price_max", e.target.value)} error={fieldErrors.price_max} maxLength={12} />
        </div>
        <div className="grid grid-cols-[7rem_1fr] gap-3">
          <SelectField label="Currency" value={brief.currency} onChange={(e) => set("currency", e.target.value)} error={fieldErrors.currency}>
            {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </SelectField>
          <TextField label="Where you'll sell" optional placeholder="United States" value={brief.market}
            onChange={(e) => set("market", e.target.value)} error={fieldErrors.market} maxLength={80} />
        </div>
      </fieldset>

      {error && <Notice tone="error" title="The draft wasn't created">{error}</Notice>}

      <div className="flex flex-wrap items-center gap-4 border-t border-rule pt-6">
        <span className="relative inline-flex rounded-sm">
          <Button type="submit" variant="stamp" busy={busy} className="h-12 px-6 text-base">
            {busy ? "Drafting your store" : "Draft my store"}
          </Button>
          <ShineBorder shineColor={["#2a45c2", "#939cdf", "#2a45c2"]} duration={9} />
        </span>
        <p className="max-w-[40ch] text-xs text-ink-2">
          You&apos;ll review the draft before anything is saved.
        </p>
      </div>
    </form>
  );
}
