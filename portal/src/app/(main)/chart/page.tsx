import { getGraphInsights } from "@/lib/cvce";
import { loadChartFromSearchParams } from "@/lib/load-chart";
import { ChartViewer } from "@/components/chart/ChartViewer";
import { GraphInsights } from "@/components/chart/GraphInsights";
import { Card } from "@/components/ui/Card";
import { Compass } from "lucide-react";

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
          <p className="mt-2 text-xs text-text-muted">
            The engine scales to zero when idle — a cold start can take a few seconds. Try again in a moment.
          </p>
        </Card>
      ) : null}

      {!chart && !error ? (
        <Card className="p-10 flex flex-col items-center text-center gap-4">
          <Compass size={36} className="text-accent/50" />
          <div>
            <p className="font-semibold text-lg">Enter birth details to cast a chart</p>
            <p className="text-sm text-text-muted mt-1">
              Fill in the date, time, and location above, then click{" "}
              <span className="font-medium text-accent">Compute chart</span>.
            </p>
          </div>
          <p className="text-xs text-text-muted font-mono">
            Swiss Ephemeris · Lahiri sidereal · PyJHora engine
          </p>
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
