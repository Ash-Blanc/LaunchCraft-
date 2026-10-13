import { Suspense } from "react";
import { DraftReview } from "@/features/onboarding/DraftReview";

export const metadata = { title: "Review draft" };

export default function DraftPage({ params }: PageProps<"/draft/[proposalId]">) {
  return (
    <Suspense fallback={null}>
      {params.then(({ proposalId }) => <DraftReview proposalId={proposalId} />)}
    </Suspense>
  );
}
