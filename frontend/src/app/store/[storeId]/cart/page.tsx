import { LiveStorefront } from "@/features/storefront/LiveStorefront";
import { loadStore } from "@/lib/server-api";

export default async function CartRoute({ params }: PageProps<"/store/[storeId]/cart">) {
  const { storeId } = await params;
  const store = await loadStore(storeId);
  return <LiveStorefront store={store} view={{ kind: "cart" }} />;
}
