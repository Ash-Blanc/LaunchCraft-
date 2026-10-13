"use client";

import Link from "next/link";

export default function StoreError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-md px-5 py-24">
      <h1 className="font-display text-3xl">This store couldn&apos;t load</h1>
      <p className="mt-3 text-sm text-ink-2">
        The Launchcraft API didn&apos;t respond. Check that the backend is running on port 8000, then try again.
      </p>
      <div className="mt-6 flex gap-4 text-sm">
        <button type="button" onClick={reset} className="h-10 rounded-sm bg-ink px-4 font-medium text-paper">Try again</button>
        <Link href="/" className="self-center underline underline-offset-4">Back to Launchcraft</Link>
      </div>
    </div>
  );
}
