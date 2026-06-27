import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import AnimatedTransitEngine from "@/components/explorers/AnimatedTransitEngine";
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
          Transits
        </h2>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? (
        <>
          <AnimatedTransitEngine chart={chart} />
          <GraphicalEphemeris chart={chart} />
        </>
      ) : null}
    </div>
  );
}
