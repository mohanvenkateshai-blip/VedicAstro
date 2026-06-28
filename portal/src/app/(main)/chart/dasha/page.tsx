import { loadChartFromSearchParams } from "@/lib/load-chart";
import { getDashaDeep, getDashaPredictions } from "@/lib/cvce";
import { Card } from "@/components/ui/Card";
import { DashaDeepTree } from "@/components/explorers/DashaDeepTree";
import { AllDashasPanel } from "@/components/explorers/AllDashasPanel";

// Allow 60s: getDashaDeep + getDashaPredictions run in parallel (~5–8s warm).
export const maxDuration = 60;

type SP = Record<string, string | string[] | undefined>;

export default async function DashaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, birth, error } = await loadChartFromSearchParams(await searchParams);

  const [dashaDeep, predictionsResp] = await Promise.all([
    chart ? getDashaDeep(birth).catch(() => null) : Promise.resolve(null),
    chart ? getDashaPredictions(birth).catch(() => null) : Promise.resolve(null),
  ]);

  // Merge transit-fused predictions into the tree nodes (level 2 only).
  if (dashaDeep && predictionsResp?.predictions) {
    const preds = predictionsResp.predictions;
    for (const maha of dashaDeep.dashaTree) {
      for (const antar of maha.subPeriods) {
        const key = `${maha.lord}/${antar.lord}`;
        antar.prediction = preds[key] ?? null;
      }
    }
  }

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Dasha Timeline
        </h2>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? (
        <>
          <DashaDeepTree chart={chart} dashaData={dashaDeep ?? undefined} />
          <AllDashasPanel chart={chart} />
        </>
      ) : null}
    </div>
  );
}
