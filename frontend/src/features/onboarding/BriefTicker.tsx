"use client";

import { TypingAnimation } from "@/components/ui/typing-animation";
import { EXAMPLE_BRIEFS } from "./examples";

const LINES = EXAMPLE_BRIEFS.map(
  (b) => `${b.business_name} — ${b.niche.charAt(0).toLowerCase()}${b.niche.slice(1)}`,
);

/**
 * A receipt-line that types real example briefs, one after another.
 * Shows what "describe the business" means before the visitor reads the form.
 */
export function BriefTicker() {
  return (
    <p className="flex min-h-[2.75rem] items-center gap-2 rounded-sm border border-rule bg-sheet px-3 py-2 text-sm">
      <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-stamp" />
      <span className="shrink-0 text-xs text-ink-2">A brief like</span>
      <TypingAnimation
        as="span"
        words={LINES}
        loop
        typeSpeed={38}
        deleteSpeed={16}
        pauseDelay={2400}
        showCursor
        blinkCursor
        className="min-w-0 truncate font-medium text-ink"
      />
    </p>
  );
}
