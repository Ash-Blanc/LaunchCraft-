import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md px-5 py-24">
      <h1 className="font-display text-3xl">Nothing at this address</h1>
      <p className="mt-3 text-sm text-ink-2">
        The store or product may have been removed, or the link has a typo.
      </p>
      <Link href="/" className="mt-6 inline-block text-sm underline underline-offset-4">Back to Launchcraft</Link>
    </div>
  );
}
