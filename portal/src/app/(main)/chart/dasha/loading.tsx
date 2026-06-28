import { Card } from "@/components/ui/Card";

export default function DashaLoading() {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Dasha Timeline
        </h2>
      </Card>

      {/* Ladder skeleton */}
      <div className="rounded-xl border border-hairline p-4 space-y-3 animate-pulse">
        <div className="h-3 w-16 rounded bg-hairline" />
        <div className="h-4 w-48 rounded bg-hairline" />
        <div className="h-4 w-36 rounded bg-hairline" />
        <div className="h-4 w-28 rounded bg-hairline" />
      </div>

      {/* Mahadasha chips skeleton */}
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 9 }).map((_, i) => (
          <div
            key={i}
            className="shrink-0 h-14 w-16 rounded-xl border border-hairline animate-pulse bg-hairline/30"
          />
        ))}
      </div>

      <p className="text-center text-xs text-text-muted font-mono animate-pulse">
        computing dasha periods…
      </p>

      {/* AllDashasPanel skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-2xl border border-hairline bg-card p-5 space-y-3 animate-pulse">
            <div className="h-4 w-24 rounded bg-hairline" />
            <div className="h-4 w-32 rounded bg-hairline" />
            <div className="h-4 w-20 rounded bg-hairline" />
          </div>
        ))}
      </div>
    </div>
  );
}
