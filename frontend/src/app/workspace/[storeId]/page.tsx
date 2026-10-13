import { Suspense } from "react";
import { Workspace } from "@/features/workspace/Workspace";

export const metadata = { title: "Workspace" };

export default function WorkspacePage({ params }: PageProps<"/workspace/[storeId]">) {
  return (
    <Suspense fallback={null}>
      {params.then(({ storeId }) => <Workspace storeId={storeId} />)}
    </Suspense>
  );
}
