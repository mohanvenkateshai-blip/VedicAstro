"use client";

import { useMemo } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { BirthForm } from "./BirthForm";
import { DEMO_BIRTH_DEFAULTS, parseBirthDefaults } from "@/lib/birth-params";

export function ChartBirthForm() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const defaults = useMemo(() => {
    const sp: Record<string, string> = {};
    searchParams.forEach((v, k) => {
      sp[k] = v;
    });
    return Object.keys(sp).length
      ? parseBirthDefaults(sp)
      : { ...DEMO_BIRTH_DEFAULTS };
  }, [searchParams]);

  return <BirthForm defaults={defaults} action={pathname} />;
}
