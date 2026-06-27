import { getGraphInsights } from "@/lib/cvce";
import { loadChartFromSearchParams } from "@/lib/load-chart";
import { GraphInsights } from "@/components/chart/GraphInsights";
import { Card } from "@/components/ui/Card";

type SP = Record<string, string | string[] | undefined>;

export default async function SourcesPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);
  const graphData = chart ? await getGraphInsights(chart).catch(() => null) : null;

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Classical Sources
        </h2>
        <p className="text-sm text-text-muted mt-1">
          GraphRAG citations from ingested shastra texts for today&apos;s transits.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {graphData ? (
        <GraphInsights data={graphData} />
      ) : (
        <Card className="p-6 text-sm text-text-muted">
          Cast a chart with birth details to load classical transit citations.
        </Card>
      )}
    </div>
  );
}
