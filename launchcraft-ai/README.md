# Launchcraft AI (working name)

From a business idea to a store ready to sell — an AI store-launch workspace with a verified PayPal Sandbox checkout.

> Hackathon project. Not affiliated with or endorsed by PayPal or Shopify. Sandbox payments only.

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Trusted backend core: money, validation, cart, order state machine, PayPal Orders v2 client, launch checks | **Done — 59 tests passing** |
| 2 | Next.js workspace, design system, live storefront preview | Not started |
| 3 | PayPal JS SDK buttons + real sandbox end-to-end run | Backend ready; needs sandbox credentials |
| 4 | AI agent with typed tools + labelled demo mode | Not started |
| 5 | Polish, accessibility, docs, clean-setup verification | Not started |

## What the backend guarantees

- **Prices never come from the client or the AI.** Checkout requests carry only product IDs and quantities; the server prices the cart from stored, validated decimals.
- **A payment is only "completed" when PayPal says so and the numbers match.** The capture response must be `COMPLETED`, and the captured amount and currency must equal the server-computed total. A `PENDING` capture or any mismatch is recorded as `FAILED`.
- **No double capture.** Orders move through a compare-and-set state machine (`PAYPAL_CREATED → CAPTURING → COMPLETED | FAILED`, or `CANCELLED`). Repeat capture calls return the recorded outcome; concurrent ones get `409`. Every PayPal mutation sends a deterministic `PayPal-Request-Id`, so a retry after a timeout is deduplicated by PayPal too.
- **Declines and outages are recoverable.** `INSTRUMENT_DECLINED` and network errors return the order to an approvable state so the buyer can retry.
- **Launch readiness is evidence-based.** Each check reports `pass`, `fail`, `warn` or `not_run` with evidence. The store is only ready after a real sandbox capture has been verified; nothing is marked passed that wasn't checked.
- **Secrets stay server-side.** The client secret is read from the environment and never returned or logged; only the public client ID is exposed (it's required by the PayPal JS SDK).

## Run the backend (Windows PowerShell)

```powershell
cd backend
py -3.12 -m venv .venv          # Python 3.11+ works
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .env   # then fill in your sandbox credentials
python -m pytest -q
uvicorn app.main:app --reload --env-file .env
```

macOS/Linux: same steps with `python3 -m venv .venv && source .venv/bin/activate`.

API docs are then at http://localhost:8000/docs.

## API (Phase 1)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | PayPal configured? AI live or demo? |
| GET | `/api/config/public` | Public PayPal client ID for the JS SDK |
| POST | `/api/stores` | Create a store from a validated configuration |
| GET | `/api/stores/{id}` | Store with products |
| POST/PUT/DELETE | `/api/stores/{id}/products[/{pid}]` | Product CRUD |
| POST | `/api/stores/{id}/checkout` | Price cart on the server, create PayPal order |
| POST | `/api/checkout/{paypal_order_id}/capture` | Capture and verify |
| POST | `/api/checkout/{paypal_order_id}/cancel` | Buyer cancelled |
| POST | `/api/stores/{id}/launch-checks` | Run the launch-readiness report |

## License

To be chosen before publishing (MIT suggested).
