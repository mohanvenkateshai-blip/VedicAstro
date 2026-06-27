import { getPrashna } from "@/lib/cvce";
import { ChartViewer } from "@/components/chart/ChartViewer";
import { Card } from "@/components/ui/Card";
import { PrashnaCaster } from "@/components/explorers/PrashnaCaster";

type SP = Record<string, string | string[] | undefined>;

function num(v: string | string[] | undefined, fallback: number) {
  const s = Array.isArray(v) ? v[0] : v;
  const n = parseFloat(s ?? "");
  return Number.isFinite(n) ? n : fallback;
}

export default async function PrashnaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const lat = num(sp.lat, 12.97);
  const lon = num(sp.lon, 77.59);
  const tz = num(sp.tz, 5.5);
  const cast = sp.cast === "1" || sp.cast === "true";

  let chart = null;
  let error: string | null = null;

  if (cast) {
    try {
      chart = await getPrashna({ lat, lon, tz });
    } catch (e) {
      error = e instanceof Error ? e.message : "Prashna cast failed";
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 space-y-6">
      <Card className="p-5">
        <h1 className="font-[family-name:var(--font-display)] font-semibold text-2xl">
          Prashna (Horary)
        </h1>
        <p className="text-sm text-text-muted mt-1">
          Cast a chart for the question moment — use your current location and time.
        </p>
      </Card>

      <PrashnaCaster lat={lat} lon={lon} tz={tz} />

      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}

      {chart ? (
        <Card className="p-5 md:p-7">
          <p className="text-xs text-text-muted mb-4 font-mono">
            Cast at {chart.meta?.birth_datetime ?? "now"}
          </p>
          <ChartViewer chart={chart} />
        </Card>
      ) : null}
    </div>
  );
}
