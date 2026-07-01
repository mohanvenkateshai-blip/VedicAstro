import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { VarshaphalaPanel } from "@/components/explorers/VarshaphalaPanel";

type SP = Record<string, string | string[] | undefined>;

export default async function SolarReturnPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const { chart, error } = await loadChartFromSearchParams(sp);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Solar Return
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Tajika Varshaphala — current basic data only
        </p>
        <p className="text-xs text-amber-400 mt-1">
          Shown: Natal Sun • Solar Return Sun/Moon • Muntha (progressed Lagna, 1 sign per year)
        </p>
        <p className="text-[11px] text-text-muted mt-2">
          Not computed yet: Patyayini dasha, Harsha Bala, Panchavargiya Bala, full annual predictions, Tajika yogas, etc.
        </p>
      </Card>

      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}

      {chart ? (
        <VarshaphalaPanel chart={chart} />
      ) : (
        <Card className="p-6 border border-hairline">
          <p className="text-sm text-text-muted">
            No birth data in the URL. Go to <strong>Chart Overview</strong>, enter birth details and Compute, then switch to the Solar Return tab.
          </p>
          <p className="text-xs text-text-muted mt-2">
            The chart parameters (date, time, lat, lon, tz, place) are passed automatically via the URL.
          </p>
        </Card>
      )}
    </div>
  );
}
