"use server";

import { getSession } from "@/lib/auth";
import { saveHoroscope } from "@/lib/auth/index";
import type { ChartData } from "@/lib/types";

export async function saveChart(name: string, chart: ChartData): Promise<{ ok: boolean; error?: string }> {
  try {
    const session = await getSession();
    if (!session) return { ok: false, error: "Sign in to save charts." };

    await saveHoroscope(session.userId, name, chart as unknown as Record<string, unknown>);
    return { ok: true };
  } catch (e: any) {
    console.error("saveChart failed:", e?.message || e);
    return { ok: false, error: e?.message?.slice(0, 100) || "Save failed" };
  }
}
