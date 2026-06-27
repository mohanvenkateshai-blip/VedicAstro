"use server";

import { revalidatePath } from "next/cache";
import { getSession } from "@/lib/auth";
import {
  ensureUser,
  saveHoroscope,
  deleteHoroscope,
  countHoroscopes,
} from "@/lib/auth/index";
import { maxSavedCharts } from "@/lib/features";
import type { ChartData } from "@/lib/types";

export async function saveChart(
  name: string,
  chart: ChartData,
): Promise<{ ok: boolean; error?: string; id?: string }> {
  try {
    const session = await getSession();
    if (!session) return { ok: false, error: "Sign in to save charts." };

    const limit = maxSavedCharts(session.role);
    const count = await countHoroscopes(session.userId);
    if (count >= limit) {
      return {
        ok: false,
        error: `Save limit reached (${limit} on ${session.role} tier). Upgrade to save more.`,
      };
    }

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

export async function deleteChart(
  id: string,
): Promise<{ ok: boolean; error?: string }> {
  try {
    const session = await getSession();
    if (!session) return { ok: false, error: "Sign in required." };

    const deleted = await deleteHoroscope(session.userId, id);
    if (!deleted) return { ok: false, error: "Chart not found." };

    revalidatePath("/dashboard");
    return { ok: true };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Delete failed";
    return { ok: false, error: msg.slice(0, 120) };
  }
}
