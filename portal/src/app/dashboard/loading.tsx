export default function Loading() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-10 animate-pulse">
      <div className="mb-8">
        <div className="h-8 w-48 bg-hairline rounded mb-2" />
        <div className="h-4 w-64 bg-hairline rounded" />
      </div>
      <div className="rounded-2xl border border-hairline">
        <div className="px-5 py-4 border-b border-hairline">
          <div className="h-5 w-24 bg-hairline rounded" />
        </div>
        <div className="p-8 space-y-3">
          <div className="h-12 bg-hairline rounded-xl" />
          <div className="h-12 bg-hairline rounded-xl" />
        </div>
      </div>
    </div>
  );
}
