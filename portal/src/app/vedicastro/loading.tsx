export default function Loading() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8 animate-pulse">
        <div className="h-4 w-36 bg-hairline rounded mb-3" />
        <div className="h-8 w-64 bg-hairline rounded mb-2" />
        <div className="h-4 w-96 bg-hairline rounded" />
      </div>
      <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
        <div className="space-y-4 animate-pulse">
          <div className="h-10 bg-hairline rounded-xl" />
          <div className="h-10 bg-hairline rounded-xl" />
          <div className="grid grid-cols-3 gap-2">
            <div className="h-10 bg-hairline rounded-xl" />
            <div className="h-10 bg-hairline rounded-xl" />
            <div className="h-10 bg-hairline rounded-xl" />
          </div>
          <div className="h-12 bg-hairline rounded-xl" />
        </div>
        <div className="min-w-0">
          <div className="rounded-2xl border border-hairline p-8 animate-pulse">
            <div className="h-[340px] bg-hairline rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  );
}
