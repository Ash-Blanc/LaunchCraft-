import { cx } from "@/components/ui";
import type { ActivityEntry } from "@/types/api";

function when(iso: string): string {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 24 * 60) return `${Math.round(mins / 60)} h ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function Timeline({ entries }: { entries: ActivityEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-xs text-ink-2">Changes you and the assistant make will be listed here.</p>;
  }
  return (
    <ol className="relative flex flex-col gap-3 border-l border-rule pl-4">
      {entries.map((a) => (
        <li key={a.id} className="relative">
          <span aria-hidden className={cx("absolute -left-[21px] top-1.5 size-2.5 rounded-full border-2 border-paper",
            a.actor === "you" ? "bg-ink" : a.actor.startsWith("assistant") ? "bg-stamp" : "bg-ink-3")} />
          <p className="text-xs leading-snug">
            <span className="font-semibold">{a.actor === "you" ? "You" : a.actor === "assistant (demo)" ? "Assistant (demo)" : "Assistant"}</span>
            {" "}{a.message.charAt(0).toLowerCase() + a.message.slice(1)}
          </p>
          {a.detail && <p className="text-xs text-ink-2">{a.detail}</p>}
          <p className="tabular text-[11px] text-ink-3">{when(a.created_at)}</p>
        </li>
      ))}
    </ol>
  );
}
