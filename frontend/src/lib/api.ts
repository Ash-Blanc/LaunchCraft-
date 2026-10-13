// Typed client for the Launchcraft API. Browser calls go to /api (proxied by Next);
// server components call the backend directly via BACKEND_URL.
import type {
  ActivityEntry, AgentAction, AgentMessageResult, AgentResult, BusinessBrief, ChangesProposal,
  DraftProposal, Health, LaunchReport, Product, ProductInput, Proposal, Store, StoreSummary, Brand,
} from "@/types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    /** Field name → message, from FastAPI 422 validation errors. */
    public fields: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const TIMEOUT_MS = 15_000;

function baseUrl(): string {
  if (typeof window !== "undefined") return "";
  return process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
}

interface FastApiValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

function cleanMessage(msg: string): string {
  return msg.replace(/^Value error, /, "").replace(/^String should have at least 1 character$/, "This field is required.");
}

async function parseError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* not JSON */
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {};
    for (const item of detail as FastApiValidationItem[]) {
      const loc = (item.loc ?? []).filter((p) => p !== "body");
      const key = loc.length ? String(loc[loc.length - 1]) : "_";
      if (!fields[key]) fields[key] = cleanMessage(item.msg ?? "Invalid value.");
    }
    const first = Object.values(fields)[0] ?? "Some fields need attention.";
    return new ApiError(first, res.status, fields);
  }
  if (typeof detail === "string") return new ApiError(detail, res.status);
  if (res.status >= 500) {
    return new ApiError("The Launchcraft API isn't responding. Check that the backend is running.", res.status);
  }
  return new ApiError(`Request failed (HTTP ${res.status}).`, res.status);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${baseUrl()}/api${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });
  } catch (e) {
    const aborted = e instanceof DOMException && e.name === "AbortError";
    throw new ApiError(
      aborted
        ? "The request took too long. Try again."
        : "Can't reach the Launchcraft API. Check that the backend is running on port 8000.",
      0,
    );
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("GET", "/health"),

  listStores: () => request<StoreSummary[]>("GET", "/stores"),
  getStore: (id: string) => request<Store>("GET", `/stores/${encodeURIComponent(id)}`),
  patchStore: (id: string, patch: { name?: string; niche?: string; audience?: string; brand?: Brand }) =>
    request<Store>("PATCH", `/stores/${encodeURIComponent(id)}`, patch),

  addProduct: (storeId: string, p: ProductInput) =>
    request<Product>("POST", `/stores/${encodeURIComponent(storeId)}/products`, p),
  updateProduct: (storeId: string, productId: string, p: ProductInput) =>
    request<Product>("PUT", `/stores/${encodeURIComponent(storeId)}/products/${encodeURIComponent(productId)}`, p),
  deleteProduct: (storeId: string, productId: string) =>
    request<void>("DELETE", `/stores/${encodeURIComponent(storeId)}/products/${encodeURIComponent(productId)}`),

  activity: (storeId: string) => request<ActivityEntry[]>("GET", `/stores/${encodeURIComponent(storeId)}/activity`),
  pendingProposals: (storeId: string) =>
    request<ChangesProposal[]>("GET", `/stores/${encodeURIComponent(storeId)}/proposals`),

  draftStore: (brief: BusinessBrief) => request<DraftProposal>("POST", "/agent/draft-store", brief),
  getProposal: (id: string) => request<Proposal>("GET", `/proposals/${encodeURIComponent(id)}`),
  acceptProposal: (id: string) =>
    request<{ proposal: Proposal; store: Store }>("POST", `/proposals/${encodeURIComponent(id)}/accept`),
  rejectProposal: (id: string) => request<Proposal>("POST", `/proposals/${encodeURIComponent(id)}/reject`),

  suggest: (storeId: string, action: AgentAction) =>
    request<AgentResult>("POST", `/stores/${encodeURIComponent(storeId)}/agent/suggest`, { action }),
  message: (storeId: string, text: string) =>
    request<AgentMessageResult>("POST", `/stores/${encodeURIComponent(storeId)}/agent/message`, { text }),

  launchChecks: (storeId: string) =>
    request<LaunchReport>("POST", `/stores/${encodeURIComponent(storeId)}/launch-checks`),
};

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return "Something unexpected went wrong. Reload the page and try again.";
}
