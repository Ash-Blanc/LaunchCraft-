"use client";

import { Button } from "@/components/ui";
import { formatPrice } from "@/lib/money";
import type { ChangesProposal, ProductInput, StoreChange } from "@/types/api";

const FIELD_LABELS: Partial<Record<keyof ProductInput, string>> = {
  name: "Name", description: "Description", price: "Price", image_url: "Image",
  image_alt: "Image description", available: "For sale",
};

function show(field: keyof ProductInput, value: unknown, currency: string): string {
  if (field === "price") return formatPrice(String(value), currency);
  if (field === "available") return value ? "Yes" : "No";
  if (value === "" || value == null) return "(empty)";
  if (field === "image_url") return String(value).split("/").pop() ?? String(value);
  return String(value);
}

function ChangeView({ change }: { change: StoreChange }) {
  if (change.op === "add_product") {
    const p = change.product;
    return (
      <div className="flex gap-3">
        {p.image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={p.image_url} alt="" className="size-14 shrink-0 bg-panel object-cover" />
        )}
        <div className="min-w-0 text-sm">
          <p className="font-medium">Add {p.name}</p>
          <p className="tabular text-ink-2">{formatPrice(p.price, p.currency)}</p>
          <p className="mt-1 line-clamp-3 text-xs text-ink-2">{p.description}</p>
        </div>
      </div>
    );
  }
  if (change.op === "update_product") {
    const fields = (Object.keys(FIELD_LABELS) as (keyof ProductInput)[])
      .filter((k) => change.before[k] !== change.after[k]);
    return (
      <div className="text-sm">
        <p className="font-medium">{change.before.name}</p>
        <dl className="mt-1.5 flex flex-col gap-2">
          {fields.map((k) => (
            <div key={k}>
              <dt className="text-xs text-ink-2">{FIELD_LABELS[k]}</dt>
              <dd className="text-xs">
                <del className="text-ink-3 decoration-fail/60">{show(k, change.before[k], change.before.currency)}</del>
                <ins className="mt-0.5 block bg-pass-wash px-1 no-underline">{show(k, change.after[k], change.after.currency)}</ins>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    );
  }
  return <p className="text-sm font-medium">Update the brand</p>;
}

export function ProposalCard({ proposal, onAccept, onReject, busy }: {
  proposal: ChangesProposal;
  onAccept: () => void;
  onReject: () => void;
  busy: "accept" | "reject" | null;
}) {
  return (
    <article className="rounded-sm border border-stamp/35 bg-sheet" aria-label={`Suggestion: ${proposal.summary}`}>
      <header className="border-b border-rule px-3.5 py-2.5">
        <p className="flex items-center gap-1.5 text-xs text-stamp">
          <span aria-hidden className="relative flex size-1.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-stamp opacity-60" />
            <span className="relative inline-flex size-1.5 rounded-full bg-stamp" />
          </span>
          Suggested change, waiting for you
        </p>
        <h3 className="mt-0.5 text-sm font-semibold">{proposal.summary}</h3>
      </header>
      <div className="flex flex-col gap-4 px-3.5 py-3">
        {proposal.rationale && <p className="text-xs leading-relaxed text-ink-2">{proposal.rationale}</p>}
        {proposal.payload.changes.map((c, i) => <ChangeView key={i} change={c} />)}
      </div>
      <footer className="flex gap-2 border-t border-rule px-3.5 py-2.5">
        <Button size="sm" variant="primary" onClick={onAccept} busy={busy === "accept"} disabled={busy !== null}>Apply</Button>
        <Button size="sm" variant="secondary" onClick={onReject} busy={busy === "reject"} disabled={busy !== null}>Dismiss</Button>
      </footer>
    </article>
  );
}
