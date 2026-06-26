import { getChart, getGraphInsights, CvceError } from "@/lib/cvce";
import { ChartViewer } from "@/components/chart/ChartViewer";
import { GraphInsights } from "@/components/chart/GraphInsights";
import { SaveChartButton } from "@/components/SaveChartButton";
import NakshatraExplorer from "@/components/explorers/NakshatraExplorer";
import RashiExplorer from "@/components/explorers/RashiExplorer";
import { DashaDeepTree } from "@/components/explorers/DashaDeepTree";
import { KootaMatcher } from "@/components/explorers/KootaMatcher";
import { SpecialPointsPanel } from "@/components/explorers/SpecialPointsPanel";
import { AllDashasPanel } from "@/components/explorers/AllDashasPanel";
import { VarshaphalaPanel } from "@/components/explorers/VarshaphalaPanel";
import AnimatedTransitEngine from "@/components/explorers/AnimatedTransitEngine";
import { GraphicalEphemeris } from "@/components/explorers/GraphicalEphemeris";
import { ExportPDFButton } from "@/components/explorers/ExportPDFButton";
import { KPExplorer } from "@/components/explorers/KPExplorer";
import { MultiChartWorksheet } from "@/components/explorers/MultiChartWorksheet";
import { BirthForm } from "@/components/BirthForm";
import { Card, CardLabel } from "@/components/ui/Card";
import { getSession } from "@/lib/auth";
import { birthInputSchema } from "@/lib/validate";
import type { BirthInput, GraphEnhancements } from "@/lib/types";

// A known-good demo birth (Mohan) so the page renders a real chart on first load.
const DEMO = {
  name: "Mohan",
  date: "1975-04-22",
  time: "19:15",
  place: "Mysore, IN",
  lat: "12.2958",
  lon: "76.6394",
  tz: "5.5",
};

type SP = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export default async function HoroscopePage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const f = {
    name: one(sp.name) ?? DEMO.name,
    date: one(sp.date) ?? DEMO.date,
    time: one(sp.time) ?? DEMO.time,
    place: one(sp.place) ?? DEMO.place,
    lat: one(sp.lat) ?? DEMO.lat,
    lon: one(sp.lon) ?? DEMO.lon,
    tz: one(sp.tz) ?? DEMO.tz,
  };

  const birthLat = Number(f.lat);
  const birthLon = Number(f.lon);
  const birthTz = Number(f.tz);
  let error: string | null = null;
  if (isNaN(birthLat) || isNaN(birthLon) || isNaN(birthTz)) {
    error = "Invalid coordinates — please check latitude, longitude, and timezone.";
  }

  const birth: BirthInput = {
    name: f.name,
    birth_datetime: `${f.date}T${(f.time || "12:00").slice(0, 5)}:00`,
    birth_lat: birthLat,
    birth_lon: birthLon,
    birth_tz: birthTz,
  };

  let chart = null;
  let graphData: GraphEnhancements | null = null;
  let session = null;
  if (!error) {
    try {
      birthInputSchema.parse(birth);
      chart = await getChart(birth);
      if (chart) {
        graphData = await getGraphInsights(chart).catch(() => null);
      }
      session = await getSession().catch(() => null);
    } catch (e) {
      error = e instanceof CvceError ? e.message : "Unexpected error computing the chart.";
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8">
        <CardLabel>VedicAstro · natal chart</CardLabel>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
          {chart?.meta?.name ? `${chart.meta.name}’s chart` : "Cast a chart"}
        </h1>
        <p className="mt-1.5 text-sm text-text-muted">
          Birth details are computed server-side by the Swiss-Ephemeris engine. The
          URL is shareable.
        </p>
        {chart && session && (
          <div className="mt-3">
            <SaveChartButton chart={chart} chartName={chart.meta?.name || f.name} />
          </div>
        )}
        {chart && !session && (
          <p className="mt-2 text-xs text-text-muted">
            <a href="/auth/signin" className="underline hover:text-accent">Sign in</a> to save this chart to your dashboard.
          </p>
        )}
      </div>

      <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
        <BirthForm defaults={f} />

        <div className="min-w-0">
          {error ? (
            <Card className="p-6 border-danger/40">
              <CardLabel>Engine error</CardLabel>
              <p className="mt-2 text-sm text-danger">{error}</p>
              <p className="mt-2 text-xs text-text-muted">
                The engine scales to zero when idle — a cold start can take a few
                seconds. Try again in a moment.
              </p>
            </Card>
          ) : chart ? (
            <>
              <Card className="p-5 md:p-7">
                <div className="flex items-center justify-between mb-4">
                  <div />
                  <ExportPDFButton chart={chart} />
                </div>
                <ChartViewer chart={chart} />
              </Card>
            </>
          ) : null}
          {graphData && <GraphInsights data={graphData} />}
          {chart && (
            <div className="mt-8 space-y-8">
              <DashaDeepTree chart={chart} />
              <AllDashasPanel chart={chart} />
              <VarshaphalaPanel chart={chart} />
              <NakshatraExplorer />
              <RashiExplorer />
              <SpecialPointsPanel chart={chart} />
              <KootaMatcher />
              <KPExplorer chart={chart} />
              <AnimatedTransitEngine chart={chart} />
              <GraphicalEphemeris chart={chart} />
              <MultiChartWorksheet chart={chart} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
