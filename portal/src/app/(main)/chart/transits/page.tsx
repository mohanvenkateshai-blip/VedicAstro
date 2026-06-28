import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { GocharPanel } from "@/components/explorers/GocharPanel";
import { GraphicalEphemeris } from "@/components/explorers/GraphicalEphemeris";

type SP = Record<string, string | string[] | undefined>;

export default async function TransitsPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Transits <span className="text-sm font-normal text-text-muted font-mono">(Gochar Phala)</span>
        </h2>
        <p className="text-sm text-text-muted mt-1">
          How today&apos;s planetary positions affect you — scored from your natal Moon sign and Ascendant.
        </p>
      </Card>

      {error && (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      )}

      {chart && (
        <>
          {/* Primary: Interpreted transit assessment */}
          <Card className="p-5">
            <GocharPanel chart={chart} />
          </Card>

          {/* Secondary: Year at a glance — planet movements */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold mb-1">Year at a Glance</h3>
            <p className="text-[11px] text-text-muted font-mono mb-4">
              Planet sign movements through {new Date().getFullYear()} — use as a reference to track when transits change.
            </p>
            <GraphicalEphemeris chart={chart} />
          </Card>
        </>
      )}
    </div>
  );
}
