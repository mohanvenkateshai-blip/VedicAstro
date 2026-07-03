import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { AshtakavargaPanel } from "@/components/explorers/AshtakavargaPanel";

type SP = Record<string, string | string[] | undefined>;

export default async function AshtakavargaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Ashtakavarga
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Sarvashtakavarga (SAV) and Bhinnashtakavarga (BAV) bindu strength boards — BPHS Ch.67-72.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? (
        <AshtakavargaPanel chart={chart} />
      ) : (
        <Card className="p-6 border border-hairline">
          <p className="text-sm text-text-muted">
            No birth data in the URL. Go to <strong>Chart Overview</strong>, enter birth details and
            Compute, then switch to the Ashtakavarga tab.
          </p>
        </Card>
      )}
    </div>
  );
}
