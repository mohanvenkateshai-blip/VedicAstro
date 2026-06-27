import { loadChartFromSearchParams } from "@/lib/load-chart";
import { ExportPDFButton } from "@/components/explorers/ExportPDFButton";
import { Card } from "@/components/ui/Card";

type SP = Record<string, string | string[] | undefined>;

export default async function ExportPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Export PDF
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Download a printable chart dossier with kundali and key details.
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? (
        <Card className="p-6 flex flex-col items-start gap-4">
          <ExportPDFButton chart={chart} />
        </Card>
      ) : null}
    </div>
  );
}
