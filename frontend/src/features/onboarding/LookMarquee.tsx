import { Marquee } from "@/components/ui/marquee";
import { THEMES } from "@/features/storefront/theme";
import type { VisualDirection } from "@/types/api";

const LOOKS: { key: VisualDirection; name: string; note: string; art: string[] }[] = [
  { key: "editorial", name: "Editorial", note: "Serif masthead, magazine grid", art: ["speckled-mug", "nesting-bowls", "pour-over-cone"] },
  { key: "botanical", name: "Botanical", note: "Soft serif type, arched images", art: ["bud-vase", "pressed-fern-cards", "herbarium-labels"] },
  { key: "workshop", name: "Workshop", note: "Bold grotesque, dense catalogue", art: ["cedar-matches", "field-notebook", "spoon-rest"] },
  { key: "playful", name: "Playful", note: "Rounded shapes, price stickers", art: ["travel-candle", "room-mist", "hand-balm"] },
  { key: "minimal", name: "Minimal", note: "One typeface, quiet list", art: ["linen-envelopes", "seed-paper-tags", "parcel"] },
];

/**
 * Scrolling strip of the five storefront looks, each card set in that look's
 * own display face with real demo artwork. Pauses on hover.
 */
export function LookMarquee() {
  return (
    <section aria-labelledby="looks-heading" className="mt-16">
      <h2 id="looks-heading" className="font-display text-xl">
        Five genuinely different storefront looks, one validated engine
      </h2>
      <p className="mt-1 max-w-[60ch] text-sm text-ink-2">
        The look is part of the validated configuration — the same trusted components render every store.
      </p>
      <div className="relative mt-5 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_6%,black_94%,transparent)]">
        <Marquee pauseOnHover className="[--duration:44s] [--gap:0.875rem] p-2">
          {LOOKS.map((l) => (
            <figure
              key={l.key}
              className="flex w-60 shrink-0 flex-col gap-3 rounded-md border border-rule bg-sheet p-4 shadow-[var(--shadow-sheet)]"
            >
              <figcaption>
                <p
                  className="text-lg leading-tight text-ink"
                  style={{
                    fontFamily: THEMES[l.key].display,
                    fontWeight: l.key === "workshop" ? 750 : l.key === "minimal" ? 300 : 400,
                  }}
                >
                  {l.name}
                </p>
                <p className="mt-0.5 text-xs text-ink-2">{l.note}</p>
              </figcaption>
              <div className="flex gap-2">
                {l.art.map((a) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img key={a} src={`/demo/${a}.svg`} alt="" className="size-14 bg-panel object-cover" />
                ))}
              </div>
            </figure>
          ))}
        </Marquee>
      </div>
    </section>
  );
}
