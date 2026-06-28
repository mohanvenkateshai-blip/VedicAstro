import { loadChartFromSearchParams } from "@/lib/load-chart";
import { getDashaDeep } from "@/lib/cvce";
import { Card } from "@/components/ui/Card";
import { DashaDeepTree } from "@/components/explorers/DashaDeepTree";
import { AllDashasPanel } from "@/components/explorers/AllDashasPanel";

// Allow 60s for SSR dasha-deep (optimized engine ~3–8s warm).
export const maxDuration = 60;

type SP = Record<string, string | string[] | undefined>;

export default async function DashaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, birth, error } = await loadChartFromSearchParams(await searchParams);

  // Prefetch dasha tree server-side — single request, cached 24h per birth.
  const dashaDeep = chart
    ? await getDashaDeep(birth).catch(() => null)
    : null;

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
