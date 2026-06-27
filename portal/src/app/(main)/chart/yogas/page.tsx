import { loadChartFromSearchParams } from "@/lib/load-chart";
import { YogasPanel } from "@/components/explorers/YogasPanel";
import { Card } from "@/components/ui/Card";

type SP = Record<string, string | string[] | undefined>;

export default async function YogasPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Yogas &amp; Strength
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Classical yogas from PyJHora, plus shadbala and ashtakavarga from the
          canonical chart payload.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? <YogasPanel chart={chart} /> : null}
    </div>
  );
}
