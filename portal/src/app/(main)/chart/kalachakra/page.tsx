import { loadChartFromSearchParams } from "@/lib/load-chart";
import { Card } from "@/components/ui/Card";
import { KalachakraDasha } from "@/components/dashas/KalachakraDasha";
import { postCvce } from "@/lib/cvce-client";
import type { SignDashaBlock } from "@/lib/types";

type SP = Record<string, string | string[] | undefined>;

export default async function KalachakraDashaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const { chart, birth, error } = await loadChartFromSearchParams(sp);

  let kalaData: SignDashaBlock | null = null;

  if (chart && birth) {
    try {
      const json = await postCvce<any>("kalachakra-dasha", {
        birth_datetime: birth.birth_datetime,
        birth_lat: birth.birth_lat,
        birth_lon: birth.birth_lon,
        birth_tz: birth.birth_tz,
      });
      if (json && json.periods) {
        kalaData = {
          maha: json.maha,
          antara: json.antara,
          mahaStart: json.mahaStart,
          mahaEnd: json.mahaEnd,
          periods: json.periods,
          dehaJeeva: json.dehaJeeva,
          graph_citations: json.graph_citations,
          ke_version: json.ke_version,
        } as any;
      }
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
          86-year sign-based cycle (BPHS Vol.2 / Phaladeepika / Deva Keralam) — Moon nakshatra-pada wheel with Deha/Jeeva.
        </p>
        <p className="text-xs text-amber-400 mt-1">
          Includes current maha/antara, full period list, Deha/Jeeva notes, and classical graph citations.
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
      ) : kalaData && (kalaData as any).status === "error" ? (
        <Card className="p-6 border border-amber-500/40">
          <p className="text-sm text-amber-600">Kalachakra calculation unavailable for this chart.</p>
          <p className="text-xs text-text-muted mt-1 font-mono">{(kalaData as any).error}</p>
        </Card>
      ) : (
        <KalachakraDasha data={kalaData} />
      )}
    </div>
  );
}
