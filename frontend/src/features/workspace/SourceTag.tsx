"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { AgentSource } from "@/types/api";

/** Says plainly where assistant output came from. Shown wherever assistant content appears. */
export function SourceTag({ source, compact }: { source: AgentSource; compact?: boolean }) {
  const tag = source === "demo" ? (
    <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-xs border border-wait/40 bg-wait-wash px-2 py-0.5 text-xs text-ink">
      <span aria-hidden className="size-1.5 rounded-full bg-wait" />
      {compact ? "Demo mode" : "Demo assistant, rule-based"}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-xs border border-stamp/30 bg-stamp-wash px-2 py-0.5 text-xs text-ink">
      <span aria-hidden className="size-1.5 rounded-full bg-stamp" />
      Live model
    </span>
  );
  return (
    <Tooltip>
      <TooltipTrigger asChild>{tag}</TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-64 rounded-xs text-xs">
        {source === "demo"
          ? "Produced by fixed rules and sample data. No language model was used."
          : "Produced by a live language model calling typed tools."}
      </TooltipContent>
    </Tooltip>
  );
}
