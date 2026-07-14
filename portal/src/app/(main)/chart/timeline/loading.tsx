export default function TimelineLoading() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading person timeline">
      <div className="h-28 animate-pulse rounded-2xl border border-hairline bg-card" />
      <div className="grid grid-cols-3 gap-3">{Array.from({ length: 3 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-xl border border-hairline bg-card" />)}</div>
      <div className="h-96 animate-pulse rounded-2xl border border-hairline bg-card" />
    </div>
  );
}
