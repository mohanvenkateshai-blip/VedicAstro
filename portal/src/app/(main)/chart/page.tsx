import { getGraphInsights } from "@/lib/cvce";
import { loadChartFromSearchParams } from "@/lib/load-chart";
import { ChartViewer } from "@/components/chart/ChartViewer";
import { GraphInsights } from "@/components/chart/GraphInsights";
import { Card } from "@/components/ui/Card";

type SP = Record<string, string | string[] | undefined>;

export default async function ChartOverviewPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);
  const graphData = chart ? await getGraphInsights(chart).catch(() => null) : null;

  return (
    <div className="space-y-6">
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? (
        <Card className="p-5 md:p-7">
          <ChartViewer chart={chart} />
        </Card>
      ) : null}
      {graphData ? <GraphInsights data={graphData} /> : null}
    </div>
  );
}
