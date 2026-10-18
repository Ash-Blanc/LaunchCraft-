// Shapes returned by the FastAPI backend. Kept in one place so a schema change is one edit.

export type VisualDirection = "editorial" | "botanical" | "workshop" | "playful" | "minimal";

export interface Brand {
  tagline: string;
  personality: string;
  visual_direction: VisualDirection;
  accent_color: string;
  ink_color: string;
  surface_color: string;
}

/** Product fields the user (or the assistant) can submit. Prices are strings, never floats. */
export interface ProductInput {
  slug: string;
  name: string;
  description: string;
  price: string;
  currency: string;
  image_url: string;
  image_alt: string;
  available: boolean;
  inventory?: number | null;
}

export interface Product extends ProductInput {
  id: string;
  inventory: number | null;
}

export interface StoreConfig {
  name: string;
  niche: string;
  audience: string;
  market: string;
  currency: string;
  brand: Brand;
  products: ProductInput[];
}

export interface Store extends Omit<StoreConfig, "products"> {
  id: string;
  updated_at: string;
  products: Product[];
}

export interface StoreSummary {
  id: string;
  name: string;
  niche: string;
  updated_at: string;
}

export interface BusinessBrief {
  business_name: string;
  niche: string;
  audience: string;
  personality: string;
  visual_direction: VisualDirection | "auto";
  example_products: string;
  price_min: string;
  price_max: string;
  currency: string;
  market: string;
}

export interface DecisionNote {
  topic: string;
  decision: string;
  reason: string;
}

export type AgentSource = "demo" | "live";
export type ProposalStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "STALE";

export type StoreChange =
  | { op: "add_product"; product: ProductInput }
  | { op: "update_product"; product_id: string; before: ProductInput; after: ProductInput }
  | { op: "update_brand"; before: Brand; after: Brand };

interface ProposalBase {
  id: string;
  store_id: string | null;
  source: AgentSource;
  summary: string;
  rationale: string;
  status: ProposalStatus;
  created_at: string;
}

export interface DraftProposal extends ProposalBase {
  kind: "generate_store";
  payload: { config: StoreConfig; notes: DecisionNote[]; brief: BusinessBrief };
}

export interface ChangesProposal extends ProposalBase {
  kind: "store_changes";
  payload: { changes: StoreChange[] };
}

export type Proposal = DraftProposal | ChangesProposal;

export type CheckStatus = "pass" | "fail" | "warn" | "not_run";

export interface CheckResult {
  id: string;
  label: string;
  status: CheckStatus;
  evidence: string;
  kind: "automated" | "verified_integration";
  required: boolean;
}

export interface LaunchReport {
  id: string;
  ready: boolean;
  results: CheckResult[];
  created_at: string;
}

export interface ActivityEntry {
  id: string;
  actor: string;
  message: string;
  detail: string;
  created_at: string;
}

export type AgentAction = "fill_missing_details" | "suggest_product" | "run_launch_checks";

export interface AgentResult {
  mode: AgentSource;
  proposal: ChangesProposal | null;
  report: LaunchReport | null;
  note?: string;
}

export interface AgentMessageResult extends AgentResult {
  reply: string;
  action: AgentAction | null;
}

export interface Health {
  ok: boolean;
  paypal_env: "sandbox";
  paypal_configured: boolean;
  ai_mode: AgentSource;
  ai_key_present: boolean;
}

/** Returned by `/api/health`. Browser-safe subset of backend config (no secrets). */
export interface PublicConfig {
  paypal_client_id: string | null;
  paypal_env: "sandbox";
}

export const ORDER_STATUSES = [
  "PAYPAL_CREATED", "CAPTURING", "COMPLETED", "FAILED", "CANCELLED",
] as const;
export type OrderStatus = typeof ORDER_STATUSES[number];

export interface OrderItem {
  product_id: string;
  slug: string;
  name: string;
  unit_price: string;
  quantity: number;
  line_total: string;
}

/** Returned from /checkout and the capture/cancel endpoints. */
export interface CheckoutOrder {
  id: string;
  store_id: string;
  status: OrderStatus;
  currency: string;
  total: string;
  items: OrderItem[];
  paypal_order_id: string | null;
  paypal_capture_id: string | null;
  captured_amount: string | null;
  failure_reason: string | null;
  /** Always true — confirmed by the backend's paypal_env guard. */
  sandbox: true;
  created_at: string;
  updated_at: string;
}

/** Cart line sent to /checkout. Server re-prices from current product data — nothing trusted from the client here. */
export interface CheckoutLine {
  product_id: string;
  quantity: number;
}
