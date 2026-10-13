# Launchcraft AI (working name)

From a business idea to a store ready to sell: an AI store-launch workspace with a verified PayPal Sandbox checkout.

> Hackathon project. Not affiliated with or endorsed by PayPal or Shopify. Sandbox payments only.

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Trusted backend core: money, validation, cart, order state machine, PayPal Orders v2 client, launch checks | Done |
| 2 | Next.js workspace: onboarding, draft review, assistant panel, catalogue and brand editors, live preview, storefront, launch docket | **Done**, demo assistant only |
| 3 | PayPal JS SDK buttons and a real sandbox end-to-end payment | Backend ready; storefront checkout button is disabled until this phase |
| 4 | Live-model assistant with typed tools (demo mode stays as fallback) | Interface in place, not started |
| 5 | Polish, accessibility audit, clean-setup verification | Not started |

**Checks run for this phase:** 84 backend tests pass; TypeScript, ESLint and `next build` are clean; a scripted headless-Chrome walkthrough (brief → draft → accept → suggest and apply → edit with validation → brand → launch checks → chat → storefront → cart, at desktop and phone widths) runs with no console errors. The presentation layer below was verified end to end against a live backend (draft → accept → workspace → storefront → launch checks → message routing → suggest and apply, all over HTTP).

## Presentation layer (shadcn/ui + Magic UI + 21st.dev)

shadcn/ui is initialised in the frontend with **every token remapped onto the house palette** (paper, ink, stamp blue — see `globals.css`), so library components look native rather than pasted on. Sources are vendored and owned, per the shadcn model.

- **shadcn/ui**: `badge` (launch-readiness and pending-suggestion counts), `tooltip` (the demo-mode source tag), `sonner` (workspace toasts, light theme), `progress` + `separator`.
- **Magic UI** (free `@magicui` registry): `typing-animation` (landing brief ticker cycling real example briefs), `marquee` (the five storefront looks strip, pause on hover), `number-ticker` (stats strip and docket counts), `shine-border` (the *Draft my store* CTA), `border-beam` (traces the live-preview pane while unsaved edits are showing).
- **21st.dev Agent Elements** (free registry, no auth): `spiral-loader` + `text-shimmer` (the assistant's *Working* state) and `suggestions` (one-click chat prompts above the input, routed through the message API). `--an-*` tokens remapped to the palette as well.
- The launch docket gained a required-checks **progress bar**; proposal cards gained a pulsing "waiting for you" dot.
- `lottie-react` is pinned to `2.4.1` (the version Agent Elements targets; v3 changed the API).
- All motion respects the existing `prefers-reduced-motion` global override.

## What works now

- **Onboarding.** Describe the business, pick a look (or let the assistant choose), optionally list products and a price range. Three example briefs fill the form in one click.
- **Draft review.** The assistant returns a *proposal*, not a store: a catalogue, a look and a short note explaining each choice, with a clickable preview. Nothing is saved until you choose **Create this store**.
- **Workspace.**
  - Assistant panel with three tools (suggest a product, fill in missing details, run launch checks) and a chat box that routes requests to those tools.
  - Every change arrives as a reviewable card showing before and after; **Apply** or **Dismiss**.
  - History tab with the full activity timeline.
- **Catalogue editor.** Add, edit and remove products with confirmation. Covers price, availability, stock, image (bundled illustrations or an https address), image description and URL name. Validation runs as you type and again on the server.
- **Brand editor.** Name, tagline, five visual directions, three colours, with a contrast warning.
- **Live preview.** Clickable storefront at desktop or phone width. Shows unsaved edits as you type, and jumps to the product you're editing.
- **Storefront** at `/store/{id}`. Five genuinely different looks rendered from validated configuration by trusted React components. Includes home, product pages, cart with an estimated subtotal, and empty and error states.
- **Launch docket.** Records each check with evidence and stamps the store *Ready* or *Not ready*. One check loads every product page from the running storefront and confirms it renders.

## What is deliberately not working yet

- **Checkout.** The cart's *Check out with PayPal* button is disabled with an explanation. No payment can be attempted, and none is ever shown as successful.
- **The assistant is rule-based.** Every assistant surface is labelled *Demo mode*. Same input gives the same output, built from hand-written sample catalogues; no language model is called, even if `AI_API_KEY` is set. `/api/health` reports `ai_mode: "demo"` until Phase 4.
- **A store can't reach *Ready*** until PayPal Sandbox credentials are set and a sandbox payment has been captured and verified. That needs Phase 3.
- **No publishing.** Launchcraft doesn't deploy stores anywhere.

## Run it (Windows PowerShell)

Two terminals. Python 3.11+ and Node 20+.

```powershell
# Terminal 1: backend
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .env      # fill in sandbox credentials when you have them
python -m pytest -q
uvicorn app.main:app --port 8000 --env-file .env
```

```powershell
# Terminal 2: frontend
cd frontend
npm install
npm run build
npm run start          # http://localhost:3000   (or `npm run dev` while editing)
```

macOS/Linux: the same steps, with `python3 -m venv .venv && source .venv/bin/activate`.

The frontend proxies `/api/*` to `BACKEND_URL` (default `http://127.0.0.1:8000`), so the browser never talks to the backend directly and no keys reach the client.

## Architecture in one paragraph

The assistant only ever **proposes**. A proposal is stored server-side and applied by trusted code only after the user accepts it. Applying re-validates every field with the same Pydantic schemas the editor uses. If the product was edited after the suggestion was made, the proposal is marked stale rather than overwriting the edit.

Prices are exact decimal strings end to end. The cart stores only product IDs and quantities. Totals for payment are computed by the server from stored prices.

More detail is in [docs/architecture.md](docs/architecture.md); design decisions are in [docs/design.md](docs/design.md).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Assistant mode and whether PayPal is configured |
| GET | `/api/config/public` | Public PayPal client ID for the JS SDK |
| GET/POST | `/api/stores` | Recent stores / create from a validated config |
| GET/PATCH | `/api/stores/{id}` | Store with products / update name, audience, brand |
| POST/PUT/DELETE | `/api/stores/{id}/products[/{pid}]` | Product CRUD |
| GET | `/api/stores/{id}/activity` | Timeline |
| POST | `/api/agent/draft-store` | Brief → store draft proposal |
| POST | `/api/stores/{id}/agent/suggest` | Run one assistant tool |
| POST | `/api/stores/{id}/agent/message` | Free-text request, routed to a tool |
| GET | `/api/stores/{id}/proposals` | Pending suggestions |
| GET | `/api/proposals/{id}` | One proposal |
| POST | `/api/proposals/{id}/accept` or `/reject` | Apply or dismiss |
| POST | `/api/stores/{id}/checkout` | Price cart on the server, create PayPal order |
| POST | `/api/checkout/{paypal_order_id}/capture` or `/cancel` | Capture and verify, or cancel |
| POST | `/api/stores/{id}/launch-checks` | Run the launch-readiness report |

## Demo imagery

Product illustrations in `frontend/public/demo/` are original. They're generated from simple geometry by `scripts/make_demo_art.py`; re-run it to regenerate them.

## License

To be chosen before publishing (MIT suggested).
