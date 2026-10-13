import "server-only";
import { notFound } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { Store } from "@/types/api";

/** Fetch a store for a server-rendered page. 404s become the not-found page. */
export async function loadStore(storeId: string): Promise<Store> {
  try {
    return await api.getStore(storeId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}
