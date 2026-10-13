"use client";

import { Button, cx } from "@/components/ui";
import type { CheckStatus, LaunchReport } from "@/types/api";

const STATUS: Record<CheckStatus, { label: string; mark: string; tone: string }> = {
  pass: { label: "Passed", mark: "✓", tone: "text-pass" },
  fail: { label: "Failed", mark: "✕", tone: "text-fail" },
  warn: { label: "Warning", mark: "!", tone: "text-wait" },
  not_run: { label: "Not run", mark: "○", tone: "text-wait" },
};

/**
 * The launch docket: a receipt-like record of the last check run.
 * The stamp reads READY only when every required check passed.
 */
export function LaunchDocket({ report, storeName, onRun, running }: {
  report: LaunchReport | null;
  storeName: string;
  onRun: () => void;
  running: boolean;
}) {
  const counts = report?.results.reduce<Record<CheckStatus, number>>(
    (acc, r) => ({ ...acc, [r.status]: acc[r.status] + 1 }),
    { pass: 0, fail: 0, warn: 0, not_run: 0 },
  );

  return (
    <div className="mx-auto w-full max-w-xl">
      <div className="relative bg-sheet shadow-[var(--shadow-sheet)]">
        <div className="perforation bg-sheet" aria-hidden style={{ transform: "translateY(-6px) scaleY(-1)" }} />
        <div className="px-6 pb-6 pt-2 sm:px-8">
          <div className="flex items-start justify-between gap-4 border-b border-dashed border-rule-strong pb-5">
            <div>
              <p className="text-xs text-ink-2">Launch docket</p>
              <h2 className="mt-1 font-display text-2xl leading-tight">{storeName}</h2>
              {report && (
                <p className="tabular mt-1 text-xs text-ink-2">
                  Checked {new Date(report.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
                </p>
              )}
            </div>
            {report && (
              <div key={report.id} aria-hidden
                className={cx("stamp stamp-in shrink-0 px-3 py-1.5 text-center font-display text-base font-semibold uppercase leading-tight tracking-wide",
                  report.ready ? "text-pass" : "text-fail")}>
                {report.ready ? <>Ready<br />to launch</> : <>Not<br />ready</>}
              </div>
            )}
          </div>

          {!report ? (
            <div className="py-10 text-center">
              <p className="font-display text-xl">No checks run yet</p>
              <p className="mx-auto mt-2 max-w-[40ch] text-sm text-ink-2">
                The checks look at your products, prices, cart maths, storefront pages and PayPal setup,
                and record what they found.
              </p>
              <Button variant="primary" className="mt-6" onClick={onRun} busy={running}>Run launch checks</Button>
            </div>
          ) : (
            <>
              <p className="sr-only" role="status">
                {report.ready ? "Ready to launch." : "Not ready to launch."} {counts!.pass} passed, {counts!.fail} failed, {counts!.not_run} not run.
              </p>
              <ol className="divide-y divide-dashed divide-rule-strong">
                {report.results.map((r) => {
                  const s = STATUS[r.status];
                  return (
                    <li key={r.id} className="grid grid-cols-[1.5rem_1fr] gap-x-2 py-3.5">
                      <span aria-hidden className={cx("pt-px text-base font-semibold leading-5", s.tone)}>{s.mark}</span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                          <p className="text-sm font-medium">{r.label}</p>
                          <p className={cx("text-xs font-semibold", s.tone)}>
                            {s.label}{!r.required && ", optional"}
                          </p>
                        </div>
                        <p className="mt-1 break-words text-xs leading-relaxed text-ink-2">{r.evidence}</p>
                        {r.kind === "verified_integration" && (
                          <p className="mt-1 text-xs text-stamp">Needs a real PayPal Sandbox result</p>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>
              <div className="tabular flex items-center justify-between border-t border-dashed border-rule-strong pt-4 text-xs text-ink-2">
                <span>{counts!.pass} passed, {counts!.fail} failed, {counts!.not_run} not run</span>
                <Button variant="secondary" size="sm" onClick={onRun} busy={running}>Run again</Button>
              </div>
            </>
          )}
        </div>
        <div className="perforation bg-sheet" aria-hidden style={{ transform: "translateY(6px)" }} />
      </div>
      <p className="mt-5 text-xs leading-relaxed text-ink-2">
        Ready means every required check passed. Launchcraft doesn&apos;t publish stores yet, and a store
        can&apos;t pass the payment check until a PayPal Sandbox payment has been captured and verified.
      </p>
    </div>
  );
}
