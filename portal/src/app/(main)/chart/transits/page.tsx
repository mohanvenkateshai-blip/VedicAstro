import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { TransitWorkspace } from "@/components/explorers/TransitWorkspace";

type SP = Record<string, string | string[] | undefined>;

export default async function TransitsPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, defaults, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Transits <span className="text-sm font-normal text-text-muted font-mono">(Gochar Phala)</span>
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Compare an unchanged natal chart with planetary positions at an explicitly chosen observation time and place.
        </p>
      </Card>

      {error && (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      )}

      {chart && <TransitWorkspace chart={chart} natalPlace={defaults.place} />}
    </div>
  );
}
