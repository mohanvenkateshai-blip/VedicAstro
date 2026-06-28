import { Card } from "@/components/ui/Card";

export default function SpecialLoading() {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">Special Points</h2>
      </Card>
      <div className="rounded-xl border border-hairline p-5 animate-pulse space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <div className="h-4 w-28 rounded bg-hairline" />
            <div className="h-4 w-20 rounded bg-hairline/60" />
          </div>
        ))}
      </div>
    </div>
  );
}
