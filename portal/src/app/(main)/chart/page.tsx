import { getChart } from "@/lib/cvce";
import { ChartViewer } from "@/components/chart/ChartViewer";
import { GraphInsights } from "@/components/chart/GraphInsights";
import { getGraphInsights } from "@/lib/cvce";
import { Card } from "@/components/ui/Card";
import type { BirthInput, GraphEnhancements } from "@/lib/types";

const DEMO: BirthInput = {
  name: "Mohan", birth_datetime: "1975-04-22T19:15:00",
  birth_lat: 12.2958, birth_lon: 76.6394, birth_tz: 5.5,
};

export default async function ChartOverviewPage() {
  let chart = null; let error: string | null = null; let graphData: GraphEnhancements | null = null;
  try {
    chart = await getChart(DEMO);
    if (chart) graphData = await getGraphInsights(chart).catch(() => null);
  } catch (e: any) { error = e.message; }
  return (
    <div className="space-y-6">
      {error ? <Card className="p-6 border-danger/40"><p className="text-sm text-danger">{error}</p></Card> : null}
      {chart ? <Card className="p-5 md:p-7"><ChartViewer chart={chart} /></Card> : null}
      {graphData ? <GraphInsights data={graphData} /> : null}
    </div>
  );
}
