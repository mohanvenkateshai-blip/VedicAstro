import { getChart } from "@/lib/cvce";
import { Card } from "@/components/ui/Card";
import { SpecialPointsPanel } from "@/components/explorers/SpecialPointsPanel";
import type { BirthInput } from "@/lib/types";

const DEMO: BirthInput = {
  name: "Mohan",
  birth_datetime: "1975-04-22T19:15:00",
  birth_lat: 12.2958,
  birth_lon: 76.6394,
  birth_tz: 5.5,
};

export default async function SpecialPointsPage() {
  let chart = null;
  let error: string | null = null;
  try {
    chart = await getChart(DEMO);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not load chart";
  }

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Special Points
        </h2>
      </Card>
      {error ? (
        <Card className="p-6 border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : null}
      {chart ? <SpecialPointsPanel chart={chart} /> : null}
    </div>
  );
}
