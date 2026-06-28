import { Card } from "@/components/ui/Card";

export default function TransitsLoading() {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">Transits</h2>
      </Card>
      <div className="rounded-xl border border-hairline p-4 animate-pulse space-y-3">
        <div className="flex gap-2 overflow-hidden">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="shrink-0 h-6 w-12 rounded bg-hairline/40" />
          ))}
        </div>
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="flex gap-2">
            <div className="h-5 w-14 rounded bg-hairline/30 shrink-0" />
            {Array.from({ length: 12 }).map((_, j) => (
              <div key={j} className="h-5 flex-1 rounded bg-hairline/20" />
            ))}
          </div>
        ))}
        <p className="text-center text-xs text-text-muted font-mono pt-2">computing ephemeris…</p>
      </div>
    </div>
  );
}
