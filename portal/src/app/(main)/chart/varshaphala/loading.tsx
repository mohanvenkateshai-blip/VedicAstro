import { Card } from "@/components/ui/Card";

export default function VarshaphalaLoading() {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">Solar Return</h2>
      </Card>
      <div className="rounded-xl border border-hairline p-6 animate-pulse space-y-4">
        <div className="h-5 w-40 rounded bg-hairline" />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-10 rounded-lg bg-hairline/40" />
          ))}
        </div>
      </div>
    </div>
  );
}
