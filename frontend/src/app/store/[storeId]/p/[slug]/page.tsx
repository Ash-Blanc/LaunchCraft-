import { notFound } from "next/navigation";
import { LiveStorefront } from "@/features/storefront/LiveStorefront";
import { loadStore } from "@/lib/server-api";

export default async function ProductRoute({ params }: PageProps<"/store/[storeId]/p/[slug]">) {
  const { storeId, slug } = await params;
  const store = await loadStore(storeId);
  if (!store.products.some((p) => p.slug === slug)) notFound();
  return <LiveStorefront store={store} view={{ kind: "product", slug }} />;
}
