import { loadChartFromSearchParams } from "@/lib/load-chart";
import { GrahaExplorer } from "@/components/explorers/GrahaExplorer";
import { Card } from "@/components/ui/Card";

type SP = Record<string, string | string[] | undefined>;

export default async function GrahaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Graha Explorer
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Planet-by-planet strength, dignity, house placement, and shadbala.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? <GrahaExplorer chart={chart} /> : null}
    </div>
  );
}
