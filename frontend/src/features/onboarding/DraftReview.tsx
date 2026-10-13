"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Notice, Wordmark } from "@/components/ui";
import { SourceTag } from "@/features/workspace/SourceTag";
import { PreviewFrame } from "@/features/storefront/PreviewFrame";
import type { StoreLike } from "@/features/storefront/Storefront";
import { THEMES } from "@/features/storefront/theme";
import { api, errorMessage } from "@/lib/api";
import { formatPrice } from "@/lib/money";
import type { DraftProposal } from "@/types/api";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready"; proposal: DraftProposal };

export function DraftReview({ proposalId }: { proposalId: string }) {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [busy, setBusy] = useState<"accept" | "discard" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    api.getProposal(proposalId)
      .then((p) => {
        if (!live) return;
        if (p.kind !== "generate_store") setState({ kind: "error", message: "This link isn't a store draft." });
        else setState({ kind: "ready", proposal: p });
      })
      .catch((e) => live && setState({ kind: "error", message: errorMessage(e) }));
    return () => { live = false; };
  }, [proposalId]);

  if (state.kind === "loading") return <ReviewSkeleton />;
  if (state.kind === "error") {
    return (
      <Shell>
        <div className="max-w-md py-16">
          <Notice tone="error" title="The draft couldn't be loaded">{state.message}</Notice>
          <Link href="/" className="mt-6 inline-block text-sm underline underline-offset-4">Start a new brief</Link>
        </div>
      </Shell>
    );
  }

  const { proposal } = state;
  const { config, notes } = proposal.payload;
  const preview: StoreLike = {
    id: `draft-${proposal.id}`, name: config.name, currency: config.currency, brand: config.brand,
    products: config.products.map((p) => ({ ...p, id: p.slug })),
  };
  const resolved = proposal.status !== "PENDING";

  async function accept() {
    setBusy("accept");
    setActionError(null);
    try {
      const { store } = await api.acceptProposal(proposal.id);
      router.push(`/workspace/${store.id}`);
    } catch (e) {
      setBusy(null);
      setActionError(errorMessage(e));
    }
  }

  async function discard() {
    setBusy("discard");
    setActionError(null);
    try {
      await api.rejectProposal(proposal.id);
      router.push("/");
    } catch (e) {
      setBusy(null);
      setActionError(errorMessage(e));
    }
  }

  return (
    <Shell wide>
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(22rem,30rem)_1fr]">
        <section className="flex flex-col gap-8 border-rule px-5 pt-8 sm:px-8 lg:min-h-0 lg:overflow-y-auto lg:border-r">
          <div>
            <SourceTag source={proposal.source} />
            <h1 className="mt-3 font-display text-3xl leading-tight">Here&apos;s a first draft of {config.name}</h1>
            <p className="mt-2 text-sm text-ink-2">{proposal.summary}</p>
          </div>

          <section aria-labelledby="why-heading">
            <h2 id="why-heading" className="text-sm font-semibold">Why it looks like this</h2>
            <dl className="mt-3 flex flex-col gap-4">
              {notes.map((n) => (
                <div key={n.topic} className="border-l-2 border-stamp pl-3">
                  <dt className="text-xs text-ink-2">{n.topic}</dt>
                  <dd className="text-sm font-medium">{n.decision}</dd>
                  <dd className="mt-0.5 text-sm text-ink-2">{n.reason}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section aria-labelledby="products-heading">
            <h2 id="products-heading" className="text-sm font-semibold">
              {config.products.length} product{config.products.length === 1 ? "" : "s"}
            </h2>
            <ul className="mt-2 divide-y divide-rule border-y border-rule">
              {config.products.map((p) => (
                <li key={p.slug} className="flex items-baseline justify-between gap-4 py-2 text-sm">
                  <span className="truncate">{p.name}</span>
                  <span className="tabular shrink-0 text-ink-2">{formatPrice(p.price, p.currency)}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-ink-2">{THEMES[config.brand.visual_direction].label}.</p>
          </section>

          {actionError && <Notice tone="error" title="That didn't work">{actionError}</Notice>}

          {resolved ? (
            <Notice title={`This draft was ${proposal.status.toLowerCase()}`}>
              {proposal.status === "ACCEPTED" && proposal.store_id
                ? <Link href={`/workspace/${proposal.store_id}`} className="underline underline-offset-4">Open the store</Link>
                : <Link href="/" className="underline underline-offset-4">Start a new brief</Link>}
            </Notice>
          ) : (
            <div className="sticky bottom-0 -mx-5 mt-auto flex flex-wrap items-center gap-3 border-t border-rule bg-paper px-5 py-4 sm:-mx-8 sm:px-8">
              <Button variant="stamp" onClick={accept} busy={busy === "accept"} disabled={busy !== null} className="h-11">
                Create this store
              </Button>
              <Link href="/" className="text-sm underline decoration-rule-strong underline-offset-4 hover:decoration-ink">Edit the brief</Link>
              <Button variant="quiet" onClick={discard} busy={busy === "discard"} disabled={busy !== null} className="ml-auto text-sm text-ink-2">
                Discard draft
              </Button>
            </div>
          )}
        </section>

        <section aria-label="Storefront preview" className="min-h-[70vh] lg:min-h-0">
          <PreviewFrame store={preview} caption={<span>Preview of the draft. Click around; nothing is saved.</span>} />
        </section>
      </div>
    </Shell>
  );
}

function Shell({ children, wide }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? "flex h-dvh flex-col" : "mx-auto w-full max-w-[90rem] px-5 sm:px-8"}>
      <header className={wide ? "flex items-center justify-between border-b border-rule px-5 py-3 sm:px-8" : "py-6"}>
        <Link href="/" aria-label="Launchcraft home"><Wordmark /></Link>
      </header>
      {children}
    </div>
  );
}

function ReviewSkeleton() {
  return (
    <div className="flex h-dvh flex-col" aria-busy="true" aria-label="Loading draft">
      <div className="border-b border-rule px-8 py-3"><div className="skeleton h-6 w-32" /></div>
      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[30rem_1fr]">
        <div className="flex flex-col gap-4 p-8">
          <div className="skeleton h-9 w-3/4" />
          <div className="skeleton h-4 w-full" />
          <div className="skeleton mt-6 h-32" />
        </div>
        <div className="hidden bg-panel lg:block" />
      </div>
    </div>
  );
}
