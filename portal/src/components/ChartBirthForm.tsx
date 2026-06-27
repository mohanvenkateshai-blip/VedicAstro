"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { BirthForm } from "./BirthForm";
import { DEMO_BIRTH_DEFAULTS, parseBirthDefaults } from "@/lib/birth-params";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";

function hasChartParams(sp: URLSearchParams): boolean {
  return Boolean(sp.get("date") && sp.get("time") && sp.get("lat") && sp.get("lon"));
}

export function ChartBirthForm() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const chartLoaded = hasChartParams(searchParams);
  const [expanded, setExpanded] = useState(!chartLoaded);

  useEffect(() => {
    setExpanded(!chartLoaded);
  }, [chartLoaded]);

  const defaults = useMemo(() => {
    const sp: Record<string, string> = {};
    searchParams.forEach((v, k) => {
      sp[k] = v;
    });
    return Object.keys(sp).length
      ? parseBirthDefaults(sp)
      : { ...DEMO_BIRTH_DEFAULTS };
  }, [searchParams]);

  if (chartLoaded && !expanded) {
    const parts = [
      defaults.date,
      defaults.time,
      defaults.place || `${defaults.lat}, ${defaults.lon}`,
    ].filter(Boolean);

    return (
      <Card className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <p className="text-sm min-w-0">
          <span className="font-medium">{defaults.name || "Birth chart"}</span>
          <span className="text-text-muted"> · {parts.join(" · ")}</span>
        </p>
        <Button
          type="button"
          variant="ghost"
          className="shrink-0 self-start sm:self-center"
          onClick={() => setExpanded(true)}
        >
          Edit birth details
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {chartLoaded ? (
        <div className="flex justify-end">
          <Button
            type="button"
            variant="ghost"
            className="text-xs text-text-muted h-8 px-2"
            onClick={() => setExpanded(false)}
          >
            Collapse form
          </Button>
        </div>
      ) : null}
      <BirthForm defaults={defaults} action={pathname} sticky={false} />
    </div>
  );
}
