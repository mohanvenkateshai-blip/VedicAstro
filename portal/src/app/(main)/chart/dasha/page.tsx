import { loadChartFromSearchParams } from "@/lib/load-chart";
import { getDashaDeep } from "@/lib/cvce";
import { Card } from "@/components/ui/Card";
import { DashaDeepTree } from "@/components/explorers/DashaDeepTree";
import { AllDashasPanel } from "@/components/explorers/AllDashasPanel";

type SP = Record<string, string | string[] | undefined>;

export default async function DashaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, birth, error } = await loadChartFromSearchParams(await searchParams);

  // Prefetch the expensive 5-level dasha tree server-side so it arrives with
  // the page — avoids the Vercel function timeout that kills client-side fetches.
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
