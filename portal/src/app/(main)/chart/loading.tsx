import { Card } from "@/components/ui/Card";

export default function ChartLoading() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* North Indian chart grid skeleton */}
      <Card className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-4 w-28 rounded bg-hairline" />
          <div className="h-4 w-20 rounded bg-hairline" />
        </div>
        <div className="grid grid-cols-4 gap-1 aspect-square max-w-xs mx-auto">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-hairline bg-hairline/20 h-16" />
          ))}
        </div>
      </Card>

      {/* Planet table skeleton */}
      <div className="rounded-xl border border-hairline p-4 space-y-2">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-3 w-12 rounded bg-hairline" />
            <div className="h-3 w-20 rounded bg-hairline" />
            <div className="h-3 w-16 rounded bg-hairline" />
          </div>
        ))}
      </div>

      <p className="text-center text-xs text-text-muted font-mono">
        computing chart — PyJHora engine…
      </p>
    </div>
  );
}
