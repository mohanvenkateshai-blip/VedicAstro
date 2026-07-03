import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { MultiChartWorksheet } from "@/components/explorers/MultiChartWorksheet";

type SP = Record<string, string | string[] | undefined>;

export default async function DivisionalChartsPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Divisional Charts
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Vargas (D-2 through D-60) — each divisional chart refines a specific life theme. Select up
          to 4 to compare side by side.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? (
        <Card className="p-5">
          <MultiChartWorksheet chart={chart} />
        </Card>
      ) : (
        <Card className="p-6 border border-hairline">
          <p className="text-sm text-text-muted">
            No birth data in the URL. Go to <strong>Chart Overview</strong>, enter birth details and
            Compute, then switch to the Divisional Charts tab.
          </p>
        </Card>
      )}
    </div>
  );
}
