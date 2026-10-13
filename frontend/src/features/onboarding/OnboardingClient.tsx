"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { api, errorMessage } from "@/lib/api";
import type { Health, StoreSummary } from "@/types/api";
import { BriefForm } from "./BriefForm";
import { loadSavedBrief } from "./examples";

const noop = () => () => {};

/** The form reads any brief saved in this tab, so it renders after hydration. */
export function BriefFormMount() {
  const hydrated = useSyncExternalStore(noop, () => true, () => false);
  if (!hydrated) {
    return (
      <div aria-busy="true" className="flex flex-col gap-6">
        <div className="skeleton h-7 w-40" />
        <div className="grid grid-cols-2 gap-5">
          {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-16" />)}
        </div>
        <div className="skeleton h-40" />
      </div>
    );
  }
  return <BriefForm initial={loadSavedBrief()} />;
}

type Loaded<T> = { state: "loading" } | { state: "ok"; data: T } | { state: "error"; message: string };

export function SystemStatus() {
  const [health, setHealth] = useState<Loaded<Health>>({ state: "loading" });
  const [stores, setStores] = useState<Loaded<StoreSummary[]>>({ state: "loading" });

  useEffect(() => {
    let live = true;
    api.health()
      .then((data) => live && setHealth({ state: "ok", data }))
      .catch((e) => live && setHealth({ state: "error", message: errorMessage(e) }));
    api.listStores()
      .then((data) => live && setStores({ state: "ok", data }))
      .catch((e) => live && setStores({ state: "error", message: errorMessage(e) }));
    return () => { live = false; };
  }, []);

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="status-heading">
        <h2 id="status-heading" className="text-sm font-semibold">This workspace</h2>
        {health.state === "loading" && <div className="skeleton mt-3 h-10" />}
        {health.state === "error" && (
          <p className="mt-2 text-sm text-fail" role="alert">{health.message}</p>
        )}
        {health.state === "ok" && (
          <dl className="mt-2 divide-y divide-rule border-y border-rule text-sm">
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-ink-2">Assistant</dt>
              <dd>{health.data.ai_mode === "demo" ? "Demo mode, rule-based" : "Live model"}</dd>
            </div>
            <div className="flex justify-between gap-4 py-2">
              <dt className="text-ink-2">PayPal</dt>
              <dd>{health.data.paypal_configured ? "Sandbox credentials set" : "Sandbox not configured"}</dd>
            </div>
          </dl>
        )}
      </section>

      {stores.state === "ok" && stores.data.length > 0 && (
        <section aria-labelledby="recent-heading">
          <h2 id="recent-heading" className="text-sm font-semibold">Continue a store</h2>
          <ul className="mt-2 divide-y divide-rule border-y border-rule">
            {stores.data.map((s) => (
              <li key={s.id}>
                <Link href={`/workspace/${s.id}`} className="group flex items-baseline justify-between gap-4 py-2.5 text-sm">
                  <span className="truncate font-medium group-hover:underline group-hover:underline-offset-4">{s.name}</span>
                  <span className="shrink-0 text-xs text-ink-3">
                    {new Date(s.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
