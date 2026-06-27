import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { DashaDeepTree } from "@/components/explorers/DashaDeepTree";
import { AllDashasPanel } from "@/components/explorers/AllDashasPanel";

type SP = Record<string, string | string[] | undefined>;

export default async function DashaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

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
          <DashaDeepTree chart={chart} />
          <AllDashasPanel chart={chart} />
        </>
      ) : null}
    </div>
  );
}
