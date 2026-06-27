"use server";

import { revalidatePath } from "next/cache";
import { getSession } from "@/lib/auth";
import { ensureUser, saveHoroscope } from "@/lib/auth/index";
import type { ChartData } from "@/lib/types";

export async function saveChart(
  name: string,
  chart: ChartData,
): Promise<{ ok: boolean; error?: string; id?: string }> {
  try {
    const session = await getSession();
    if (!session) return { ok: false, error: "Sign in to save charts." };

    await ensureUser(session.userId, session.email);
    const id = await saveHoroscope(
      session.userId,
      name,
      chart as unknown as Record<string, unknown>,
    );
    if (!id) {
      return { ok: false, error: "Chart was not persisted — try again." };
    }

    revalidatePath("/dashboard");
    return { ok: true, id };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Save failed";
    console.error("saveChart failed:", msg);
    return { ok: false, error: msg.slice(0, 120) };
  }
}
