"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Notice, Wordmark, cx } from "@/components/ui";
import { LaunchDocket } from "@/features/launch-readiness/LaunchDocket";
import { BrandEditor } from "@/features/store-editor/BrandEditor";
import { CatalogueList } from "@/features/store-editor/CatalogueList";
import { ProductForm } from "@/features/store-editor/ProductForm";
import { PreviewFrame } from "@/features/storefront/PreviewFrame";
import type { StoreLike } from "@/features/storefront/Storefront";
import { api, ApiError, errorMessage } from "@/lib/api";
import type {
  ActivityEntry, AgentAction, AgentSource, Brand, ChangesProposal, LaunchReport, Product, ProductInput, Store,
} from "@/types/api";
import { AssistantPanel, type ThreadItem } from "./AssistantPanel";

type Tab = "products" | "brand" | "launch";
type Pane = "assistant" | "edit" | "preview";
type Editing = { kind: "none" } | { kind: "new" } | { kind: "edit"; product: Product };

let seq = 0;
const nextId = () => `m${++seq}`;

export function Workspace({ storeId }: { storeId: string }) {
  const [store, setStore] = useState<Store | null>(null);
  const [loadError, setLoadError] = useState<{ message: string; notFound: boolean } | null>(null);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [pending, setPending] = useState<ChangesProposal[]>([]);
  const [mode, setMode] = useState<AgentSource>("demo");
  const [report, setReport] = useState<LaunchReport | null>(null);

  const [tab, setTab] = useState<Tab>("products");
  const [pane, setPane] = useState<Pane>("edit");
  const [editing, setEditing] = useState<Editing>({ kind: "none" });
  const [productDraft, setProductDraft] = useState<ProductInput | null>(null);
  const [brandDraft, setBrandDraft] = useState<{ name: string; brand: Brand } | null>(null);
  const [brandKey, setBrandKey] = useState(0);

  const [thread, setThread] = useState<ThreadItem[]>([]);
  const [running, setRunning] = useState<AgentAction | "message" | null>(null);
  const [proposalBusy, setProposalBusy] = useState<{ id: string; kind: "accept" | "reject" } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [recentId, setRecentId] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, a, p] = await Promise.all([api.getStore(storeId), api.activity(storeId), api.pendingProposals(storeId)]);
      setStore(s);
      setActivity(a);
      setPending(p);
      setLoadError(null);
      return s;
    } catch (e) {
      setLoadError({ message: errorMessage(e), notFound: e instanceof ApiError && e.status === 404 });
      return null;
    }
  }, [storeId]);

  useEffect(() => {
    let live = true;
    Promise.all([api.getStore(storeId), api.activity(storeId), api.pendingProposals(storeId), api.health()])
      .then(([s, a, p, h]) => {
        if (!live) return;
        setStore(s); setActivity(a); setPending(p); setMode(h.ai_mode);
      })
      .catch((e) => live && setLoadError({ message: errorMessage(e), notFound: e instanceof ApiError && e.status === 404 }));
    return () => { live = false; };
  }, [storeId]);

  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  function flash(message: string) {
    if (!message) return;
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3200);
  }

  // --- the preview shows unsaved edits on top of saved data ---------------------------
  const previewStore: StoreLike | null = useMemo(() => {
    if (!store) return null;
    let products: StoreLike["products"] = store.products.map((p) => ({ ...p }));
    if (productDraft && editing.kind === "edit") {
      products = products.map((p) => p.id === editing.product.id ? { ...p, ...productDraft, id: p.id } : p);
    } else if (productDraft && editing.kind === "new" && productDraft.name) {
      products = [...products, { ...productDraft, id: "__new__", slug: productDraft.slug || "__new__" }];
    }
    return {
      id: store.id,
      name: brandDraft?.name || store.name,
      currency: store.currency,
      brand: brandDraft?.brand ?? store.brand,
      products,
    };
  }, [store, productDraft, brandDraft, editing]);

  const unsaved = !!productDraft || !!brandDraft;
  const focusSlug = editing.kind !== "none" && productDraft?.name
    ? (editing.kind === "edit" ? (productDraft.slug || editing.product.slug) : productDraft.slug || "__new__")
    : null;

  // --- actions ------------------------------------------------------------------------
  async function afterEdit(message: string) {
    setEditing({ kind: "none" });
    setProductDraft(null);
    if (message) {
      await refresh();
      flash(message);
    }
  }

  async function runAction(action: AgentAction) {
    setRunning(action);
    try {
      const r = await api.suggest(storeId, action);
      setMode(r.mode);
      if (r.report) {
        setReport(r.report);
        setTab("launch");
        setPane("edit");
        setThread((t) => [...t, { id: nextId(), role: "assistant", text: reportLine(r.report!) }]);
      } else if (r.proposal) {
        setThread((t) => [...t, { id: nextId(), role: "assistant", text: `Suggested: ${r.proposal!.summary}. Nothing changes until you choose Apply.` }]);
      } else if (r.note) {
        setThread((t) => [...t, { id: nextId(), role: "assistant", text: r.note! }]);
      }
      await refresh();
    } catch (e) {
      setThread((t) => [...t, { id: nextId(), role: "assistant", text: errorMessage(e), tone: "error" }]);
    } finally {
      setRunning(null);
    }
  }

  async function sendMessage(text: string): Promise<boolean> {
    setRunning("message");
    setThread((t) => [...t, { id: nextId(), role: "you", text }]);
    try {
      const r = await api.message(storeId, text);
      setMode(r.mode);
      const extra = r.report ? ` ${reportLine(r.report)}` : r.note ? ` ${r.note}` : "";
      setThread((t) => [...t, { id: nextId(), role: "assistant", text: r.reply + extra }]);
      if (r.report) { setReport(r.report); setTab("launch"); }
      await refresh();
      return true;
    } catch (e) {
      setThread((t) => [...t, { id: nextId(), role: "assistant", text: errorMessage(e), tone: "error" }]);
      return false;
    } finally {
      setRunning(null);
    }
  }

  async function resolveProposal(p: ChangesProposal, kind: "accept" | "reject") {
    setProposalBusy({ id: p.id, kind });
    try {
      if (kind === "accept") {
        const { store: s } = await api.acceptProposal(p.id);
        const added = p.payload.changes.find((c) => c.op === "add_product");
        if (added && added.op === "add_product") {
          setRecentId(s.products.find((x) => x.slug === added.product.slug)?.id ?? null);
        }
        flash(`Applied: ${p.summary}`);
        setThread((t) => [...t, { id: nextId(), role: "assistant", text: `Applied: ${p.summary}.` }]);
      } else {
        await api.rejectProposal(p.id);
        flash("Suggestion dismissed");
        setThread((t) => [...t, { id: nextId(), role: "assistant", text: `Dismissed: ${p.summary}. Nothing was changed.` }]);
      }
    } catch (e) {
      setThread((t) => [...t, { id: nextId(), role: "assistant", text: errorMessage(e), tone: "error" }]);
    } finally {
      setProposalBusy(null);
      await refresh();
    }
  }

  async function runChecks() {
    setRunning("run_launch_checks");
    try {
      const r = await api.launchChecks(storeId);
      setReport(r);
      await refresh();
    } catch (e) {
      flash(errorMessage(e));
    } finally {
      setRunning(null);
    }
  }

  // --- render -------------------------------------------------------------------------
  if (loadError && !store) {
    return (
      <div className="mx-auto max-w-md px-5 py-24">
        <Link href="/"><Wordmark /></Link>
        <h1 className="mt-10 font-display text-3xl">{loadError.notFound ? "This store doesn't exist" : "The workspace couldn't load"}</h1>
        <p className="mt-3 text-sm text-ink-2">{loadError.notFound ? "It may have been created on another machine or with a different database." : loadError.message}</p>
        <div className="mt-6 flex items-center gap-4">
          {!loadError.notFound && <Button onClick={() => void refresh()}>Try again</Button>}
          <Link href="/" className="text-sm underline underline-offset-4">Start a new store</Link>
        </div>
      </div>
    );
  }
  if (!store || !previewStore) return <WorkspaceSkeleton />;

  const takenSlugs = store.products.filter((p) => editing.kind !== "edit" || p.id !== editing.product.id).map((p) => p.slug);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center gap-3 border-b border-rule bg-paper px-4 py-2.5 sm:gap-5 sm:px-5">
        <Link href="/" aria-label="Launchcraft home"><Wordmark className="text-base" /></Link>
        <span aria-hidden className="h-5 w-px bg-rule-strong" />
        <h1 className="min-w-0 truncate text-sm font-semibold">{store.name}</h1>
        <div className="ml-auto flex items-center gap-3">
          {report && (
            <span className={cx("hidden text-xs font-medium sm:inline", report.ready ? "text-pass" : "text-fail")}>
              {report.ready ? "Ready to launch" : "Not ready to launch"}
            </span>
          )}
          <a href={`/store/${store.id}`} target="_blank" rel="noopener noreferrer"
            className="text-sm underline decoration-rule-strong underline-offset-4 hover:decoration-ink">
            Open storefront<span className="sr-only"> (opens in a new tab)</span>
          </a>
        </div>
      </header>

      {/* Pane switcher for screens too narrow for all three panes */}
      <nav aria-label="Workspace panes" className="flex border-b border-rule xl:hidden">
        {(["assistant", "edit", "preview"] as const).map((p) => (
          <button key={p} type="button" aria-pressed={pane === p} onClick={() => setPane(p)}
            className={cx("h-10 flex-1 text-sm capitalize", p === "assistant" && "lg:hidden",
              pane === p ? "border-b-2 border-ink font-semibold" : "text-ink-2")}>
            {p === "edit" ? "Edit" : p}
            {p === "assistant" && pending.length > 0 && <span className="ml-1 text-stamp">({pending.length})</span>}
          </button>
        ))}
      </nav>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[21rem_1fr] xl:grid-cols-[21rem_minmax(26rem,1fr)_minmax(30rem,1.15fr)]">
        <aside aria-label="Assistant"
          className={cx("min-h-0 flex-col border-rule bg-panel/60 lg:flex lg:border-r", pane === "assistant" ? "flex" : "hidden")}>
          <AssistantPanel mode={mode} thread={thread} pending={pending} activity={activity}
            runningAction={running} onAction={runAction} onMessage={sendMessage}
            onAccept={(p) => resolveProposal(p, "accept")} onReject={(p) => resolveProposal(p, "reject")}
            proposalBusy={proposalBusy} />
        </aside>

        <section aria-label="Editor"
          className={cx("min-h-0 flex-col border-rule xl:flex xl:border-r",
            pane === "edit" ? "flex" : "hidden", pane === "assistant" && "lg:flex", pane === "preview" && "lg:hidden")}>
          <div role="tablist" aria-label="Editor sections" className="flex gap-5 border-b border-rule px-5 text-sm sm:px-7">
            {([["products", "Products"], ["brand", "Brand"], ["launch", "Launch checks"]] as const).map(([t, label]) => (
              <button key={t} type="button" role="tab" aria-selected={tab === t}
                onClick={() => { setTab(t); }}
                className={cx("h-11 border-b-2", tab === t ? "border-ink font-semibold" : "border-transparent text-ink-2 hover:text-ink")}>
                {label}
              </button>
            ))}
          </div>
          <div className={cx("min-h-0 flex-1 overflow-y-auto px-5 py-7 sm:px-7", tab === "launch" && "bg-panel/60")}>
            {tab === "products" && (editing.kind === "none" ? (
              <CatalogueList products={store.products} currency={store.currency} highlightId={recentId}
                onAdd={() => { setEditing({ kind: "new" }); setProductDraft(null); }}
                onEdit={(p) => { setEditing({ kind: "edit", product: p }); setProductDraft(null); setRecentId(null); }} />
            ) : (
              <ProductForm key={editing.kind === "edit" ? editing.product.id : "new"} storeId={store.id}
                currency={store.currency} product={editing.kind === "edit" ? editing.product : null}
                takenSlugs={takenSlugs} onDraft={setProductDraft} onDone={(m) => void afterEdit(m)} />
            ))}
            {tab === "brand" && (
              <BrandEditor key={`${brandKey}-${store.updated_at}`} store={store} onDraft={setBrandDraft}
                onSaved={async (m) => { setBrandDraft(null); await refresh(); setBrandKey((k) => k + 1); flash(m); }} />
            )}
            {tab === "launch" && (
              <LaunchDocket report={report} storeName={store.name} onRun={runChecks} running={running === "run_launch_checks"} />
            )}
          </div>
        </section>

        <section aria-label="Storefront preview"
          className={cx("min-h-0 flex-col xl:flex", pane === "preview" ? "flex" : "hidden")}>
          <PreviewFrame store={previewStore} focusSlug={tab === "products" ? focusSlug : null}
            highlightProductId={recentId}
            caption={unsaved
              ? <span className="font-medium text-stamp">Showing unsaved changes</span>
              : <span>Live preview</span>} />
        </section>
      </div>

      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-5 flex justify-center px-4">
        {toast && (
          <p className="rounded-sm bg-ink px-4 py-2.5 text-sm text-paper shadow-[var(--shadow-pop)]">{toast}</p>
        )}
      </div>
      {loadError && store && (
        <div className="fixed bottom-5 right-5 max-w-sm">
          <Notice tone="error" title="Couldn't refresh the workspace">{loadError.message}</Notice>
        </div>
      )}
    </div>
  );
}

function reportLine(r: LaunchReport): string {
  const passed = r.results.filter((x) => x.status === "pass").length;
  const failed = r.results.filter((x) => x.status === "fail").length;
  const notRun = r.results.filter((x) => x.status === "not_run").length;
  return r.ready
    ? `All ${passed} checks passed. The full docket is in Launch checks.`
    : `${passed} passed, ${failed} failed, ${notRun} not run. The docket in Launch checks lists what's missing.`;
}

function WorkspaceSkeleton() {
  return (
    <div className="flex h-dvh flex-col" aria-busy="true" aria-label="Loading workspace">
      <div className="flex items-center gap-4 border-b border-rule px-5 py-3">
        <div className="skeleton h-5 w-28" /><div className="skeleton h-4 w-40" />
      </div>
      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[21rem_1fr] xl:grid-cols-[21rem_1fr_1.15fr]">
        <div className="hidden flex-col gap-2 border-r border-rule bg-panel/60 p-4 lg:flex">
          {[0, 1, 2].map((i) => <div key={i} className="skeleton h-12" />)}
        </div>
        <div className="flex flex-col gap-3 p-7">
          <div className="skeleton h-8 w-40" />
          {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-14" />)}
        </div>
        <div className="hidden bg-panel xl:block" />
      </div>
    </div>
  );
}
