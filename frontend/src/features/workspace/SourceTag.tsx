import type { AgentSource } from "@/types/api";

/** Says plainly where assistant output came from. Shown wherever assistant content appears. */
export function SourceTag({ source, compact }: { source: AgentSource; compact?: boolean }) {
  if (source === "demo") {
    return (
      <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xs border border-wait/40 bg-wait-wash px-2 py-0.5 text-xs text-ink"
        title="Produced by fixed rules and sample data. No language model was used.">
        <span aria-hidden className="size-1.5 rounded-full bg-wait" />
        {compact ? "Demo mode" : "Demo assistant, rule-based"}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-xs border border-stamp/30 bg-stamp-wash px-2 py-0.5 text-xs text-ink">
      <span aria-hidden className="size-1.5 rounded-full bg-stamp" />
      Live model
    </span>
  );
}
