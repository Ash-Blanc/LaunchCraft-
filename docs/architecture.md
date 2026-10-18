# Architecture

## Shape

```
Browser ──► Next.js (frontend/)  ──/api/* rewrite──►  FastAPI (backend/)  ──►  SQLite
              │  server components fetch                │
              │  the store for /store/* pages           ├─► PayPal Orders v2 (sandbox)
              └─ client components for the workspace    └─► GET frontend product pages (render check)
```

- The frontend holds no secrets. `/api/*` is proxied to `BACKEND_URL`.
- Storefront pages are server-rendered, so their HTML contains the product data. The launch check `storefront.renders` relies on this.

## Trust boundaries

| Data | Who may produce it | Who decides it's valid |
|---|---|---|
| Store config, products | User, assistant | `schemas/store.py` (Pydantic), on every write |
| Prices | User, assistant | `core/money.py`: Decimal only, currency precision, limits |
| Cart contents | Buyer (IDs and quantities only) | `services/cart.py` prices them from the DB |
| Payment success | PayPal | `services/checkout.verify_capture`: status, order ID, amount and currency must all match |
| "Ready to launch" | Nobody asserts it | `services/launch_checks.py`: every required check must pass with evidence |

## Assistant

```
services/agent/base.py      StoreAgent protocol: generate_store, suggest, interpret_message
services/agent/demo.py      DemoAgent: deterministic rules + sample catalogues
services/agent/__init__.py  get_agent(settings) → DemoAgent (Phase 4 adds a live implementation)
services/proposals.py       accept/reject; the only path from assistant output to stored data
```

**Tools.** The tools are a closed set: `suggest_product`, `fill_missing_details` and `run_launch_checks`.

**Changes.** Suggestions are typed changes (`add_product`, `update_product`, `update_brand`), validated as a discriminated union. They're stored as a `Proposal` with `status=PENDING`. Accepting re-validates and applies them in one transaction.

**Stale proposals.** Each `update_product` carries a `before` snapshot. If the stored product no longer matches it, the proposal becomes `STALE` and nothing is written.

**Labelling.** Every proposal records `source` (`demo` or `live`). The UI shows it, and the activity log attributes actions to "assistant (demo)".

## Order lifecycle (Phase 1)

```
PAYPAL_CREATED ──capture──► CAPTURING ──verified──► COMPLETED
      │                        │  └──mismatch/declined-final──► FAILED
      └──cancel──► CANCELLED   └──decline/timeout──► PAYPAL_CREATED (retry)
```

Transitions are compare-and-set updates, so concurrent captures get `409`. PayPal calls send a deterministic `PayPal-Request-Id`, so retries are deduplicated on PayPal's side too.

## Checkout (Phase 3)

PayPal Smart Buttons on the storefront create the order on our server, hand the resulting `paypal_order_id` to the SDK for the approval UX, and on `onApprove` call `/api/checkout/{id}/capture` for the verification step. **The browser only ever carries product ids and quantities** — prices and totals are recomputed from the database at create-time and matched on capture. `verify_capture` requires:

- PayPal status `COMPLETED`,
- captured `currency_code == order.currency`,
- captured `value == Decimal(order.total)`,

or the order moves to `FAILED` with the reason. Replays of capture on a terminal order are idempotent and never re-charge. The `onCancel` path transitions `PAYPAL_CREATED → CANCELLED` so a buyer who backs out of the popup doesn't leave a dangling order.

## Frontend layout

```
src/app/                       routes: / (onboarding), /draft/[id], /workspace/[id], /store/[id]{,/p/[slug],/cart}
src/features/onboarding/       brief form, examples, draft review
src/features/workspace/        workspace shell, assistant panel, proposal cards, timeline
src/features/store-editor/     catalogue list, product form, brand editor, client-side validation
src/features/storefront/       Storefront (shared by preview and live pages), themes, cart hook
src/features/launch-readiness/ launch docket
src/lib/                       typed API client, money formatting
```

Next.js 16 runs with Cache Components. Pages that read route params do so inside `<Suspense>` or under a `loading.tsx`, which `next build` enforces.
