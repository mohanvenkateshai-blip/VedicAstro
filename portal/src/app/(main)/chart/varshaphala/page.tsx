import { loadChartFromSearchParams } from "@/lib/load-chart";
import { requireSession } from "@/lib/auth/index";
import { Card } from "@/components/ui/Card";
import { VarshaphalaPanel } from "@/components/explorers/VarshaphalaPanel";

type SP = Record<string, string | string[] | undefined>;

export default async function VarshaphalaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const session = await requireSession("pro");
  const { chart, error } = await loadChartFromSearchParams(await searchParams);

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Varshaphala
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Solar return analysis · {session.role} tier
        </p>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? <VarshaphalaPanel chart={chart} /> : null}
    </div>
  );
}
