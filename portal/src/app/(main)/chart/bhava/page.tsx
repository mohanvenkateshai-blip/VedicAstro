import { loadChartFromSearchParams } from "@/lib/load-chart";
import { BhavaExplorer } from "@/components/explorers/BhavaExplorer";
import { Card } from "@/components/ui/Card";

type SP = Record<string, string | string[] | undefined>;

export default async function BhavaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Bhava Explorer
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Inspect each house — sign, lord, occupants, and SAV bindus.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? <BhavaExplorer chart={chart} /> : null}
    </div>
  );
}
