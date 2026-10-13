"use client";

import { NumberTicker } from "@/components/ui/number-ticker";

const STATS: { value: number; label: string }[] = [
  { value: 84, label: "backend tests passing" },
  { value: 5, label: "storefront looks" },
  { value: 3, label: "assistant tools" },
  { value: 0, label: "secrets in the browser" },
];

/** Counting stats strip. Numbers animate up once, on view. */
export function StatRow() {
  return (
    <dl className="mt-14 grid grid-cols-2 gap-x-6 gap-y-5 border-y border-rule py-6 sm:grid-cols-4">
      {STATS.map((s) => (
        <div key={s.label}>
          <dt className="sr-only">{s.label}</dt>
          <dd>
            <span className="font-display text-3xl leading-none text-ink">
              <NumberTicker value={s.value} className="tabular" />
            </span>
            <span className="mt-1.5 block text-xs text-ink-2">{s.label}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}
