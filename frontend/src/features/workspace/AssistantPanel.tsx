"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, Notice, cx } from "@/components/ui";
import type { ActivityEntry, AgentAction, AgentSource, ChangesProposal } from "@/types/api";
import { ProposalCard } from "./ProposalCard";
import { SourceTag } from "./SourceTag";
import { Timeline } from "./Timeline";

export interface ThreadItem {
  id: string;
  role: "you" | "assistant";
  text: string;
  tone?: "error";
}

const ACTIONS: { action: AgentAction; label: string; hint: string }[] = [
  { action: "suggest_product", label: "Suggest a product", hint: "Proposes one new item for your review" },
  { action: "fill_missing_details", label: "Fill in missing details", hint: "Descriptions, images and alt text" },
  { action: "run_launch_checks", label: "Run launch checks", hint: "Records what passes and what doesn't" },
];

export function AssistantPanel({
  mode, thread, pending, activity, runningAction, onAction, onMessage, onAccept, onReject, proposalBusy,
}: {
  mode: AgentSource;
  thread: ThreadItem[];
  pending: ChangesProposal[];
  activity: ActivityEntry[];
  runningAction: AgentAction | "message" | null;
  onAction: (a: AgentAction) => void;
  onMessage: (text: string) => Promise<boolean>;
  onAccept: (p: ChangesProposal) => void;
  onReject: (p: ChangesProposal) => void;
  proposalBusy: { id: string; kind: "accept" | "reject" } | null;
}) {
  const [text, setText] = useState("");
  const [tab, setTab] = useState<"assistant" | "history">("assistant");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [thread.length, pending.length]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    const ok = await onMessage(t);
    if (ok) setText("");
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-rule px-4 py-2">
        <div role="tablist" aria-label="Assistant panel" className="flex gap-4 text-sm">
          {(["assistant", "history"] as const).map((t) => (
            <button key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => setTab(t)}
              className={cx("h-8 whitespace-nowrap border-b-2 capitalize", tab === t ? "border-ink font-semibold" : "border-transparent text-ink-2 hover:text-ink")}>
              {t === "history" ? `History${activity.length ? ` (${activity.length})` : ""}` : "Assistant"}
            </button>
          ))}
        </div>
        <SourceTag source={mode} compact />
      </div>

      {tab === "history" ? (
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <Timeline entries={activity} />
        </div>
      ) : (
        <>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4" aria-live="polite">
            {mode === "demo" && thread.length === 0 && (
              <p className="mb-4 text-xs leading-relaxed text-ink-2">
                The assistant is in demo mode: it follows fixed rules and sample data instead of a language model.
                It can only suggest changes; you decide what gets applied.
              </p>
            )}

            <ul className="flex flex-col gap-1.5">
              {ACTIONS.map((a) => (
                <li key={a.action}>
                  <button type="button" onClick={() => onAction(a.action)} disabled={runningAction !== null}
                    className="group flex w-full items-center justify-between gap-3 rounded-sm border border-rule bg-sheet px-3 py-2 text-left transition-colors hover:border-ink disabled:cursor-wait disabled:opacity-60">
                    <span>
                      <span className="block text-sm font-medium">{a.label}</span>
                      <span className="block text-xs text-ink-2">{a.hint}</span>
                    </span>
                    {runningAction === a.action && <span className="text-xs text-ink-2">Working</span>}
                  </button>
                </li>
              ))}
            </ul>

            {thread.length > 0 && (
              <ol className="mt-6 flex flex-col gap-3">
                {thread.map((m) => (
                  <li key={m.id} className={cx("max-w-[92%] text-sm leading-relaxed",
                    m.role === "you" ? "self-end rounded-sm bg-ink px-3 py-2 text-paper" : "self-start")}>
                    {m.role === "assistant" && m.tone === "error"
                      ? <Notice tone="error">{m.text}</Notice>
                      : m.text}
                  </li>
                ))}
              </ol>
            )}

            {pending.length > 0 && (
              <div className="mt-6 flex flex-col gap-3">
                {pending.map((p) => (
                  <ProposalCard key={p.id} proposal={p}
                    onAccept={() => onAccept(p)} onReject={() => onReject(p)}
                    busy={proposalBusy?.id === p.id ? proposalBusy.kind : null} />
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={send} className="border-t border-rule p-3">
            <label htmlFor="assistant-input" className="sr-only">Ask the assistant</label>
            <div className="flex gap-2">
              <input id="assistant-input" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000}
                placeholder={mode === "demo" ? "Try: are we ready to launch?" : "Ask for a change"}
                className="h-10 min-w-0 flex-1 rounded-sm border border-rule-strong bg-sheet px-3 text-sm placeholder:text-ink-3 focus:border-ink focus:outline-none" />
              <Button type="submit" busy={runningAction === "message"} disabled={!text.trim() || runningAction !== null}>Send</Button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
