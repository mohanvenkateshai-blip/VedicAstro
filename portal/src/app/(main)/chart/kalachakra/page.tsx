import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { KalachakraDashboard } from "@/components/dashas/kalachakra/KalachakraDashboard";
import { getKalachakraDeep } from "@/lib/cvce";
import type { KalachakraDeepData } from "@/lib/types";

type SP = Record<string, string | string[] | undefined>;

export default async function KalachakraDashaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const { chart, birth, error } = await loadChartFromSearchParams(sp);

  let kalaData: KalachakraDeepData | null = null;

  if (chart && birth) {
    try {
      kalaData = await getKalachakraDeep(birth);
    } catch {
      kalaData = null;
    }
  }

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Kalachakra Dasha
        </h2>
        <p className="text-sm text-text-muted mt-1">
          86-year sign-based cycle (BPHS Vol.2 Ch.46/49) — Moon nakshatra-pada wheel with Deha/Jeeva and the three Gatis.
        </p>
        <p className="text-xs text-amber-400 mt-1">
          Includes the current Mahadasha → Antardasha → Pratyantardasha ladder, the full leap-flagged tree, and a past/future leap timeline.
        </p>
      </Card>

      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}

      {!chart ? (
        <Card className="p-6 border border-hairline">
          <p className="text-sm text-text-muted">
            No birth data in the URL. Go to <strong>Chart Overview</strong>, enter birth details and Compute, then switch to the Kalachakra Dasha tab.
          </p>
        </Card>
      ) : kalaData ? (
        <KalachakraDashboard data={kalaData} />
      ) : (
        <Card className="p-6 border border-amber-500/40">
          <p className="text-sm text-amber-600">Kalachakra calculation unavailable for this chart.</p>
        </Card>
      )}
    </div>
  );
}
