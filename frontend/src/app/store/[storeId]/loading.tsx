export default function StoreLoading() {
  return (
    <div className="flex min-h-full flex-1 flex-col" aria-busy="true" aria-label="Loading store">
      <div className="flex items-center justify-between border-b border-rule px-5 py-4">
        <div className="skeleton h-5 w-36" />
        <div className="skeleton h-4 w-16" />
      </div>
      <div className="px-5 pt-12">
        <div className="skeleton h-12 w-2/3 max-w-lg" />
        <div className="skeleton mt-4 h-4 w-1/2 max-w-sm" />
        <div className="mt-12 grid grid-cols-2 gap-6 md:grid-cols-3">
          {[0, 1, 2].map((i) => <div key={i} className="skeleton aspect-[4/5]" />)}
        </div>
      </div>
    </div>
  );
}
