import { Card } from "@/components/ui/Card";

export default function YogasLoading() {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">Yogas & Strength</h2>
      </Card>
      <div className="space-y-3 animate-pulse">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-hairline p-4 flex gap-3">
            <div className="h-4 w-32 rounded bg-hairline" />
            <div className="h-4 flex-1 rounded bg-hairline/50" />
          </div>
        ))}
      </div>
    </div>
  );
}
