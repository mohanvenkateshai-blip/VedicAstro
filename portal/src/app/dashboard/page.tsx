import { getSession } from "@/lib/auth";
import { getHoroscopes, dbHealthy } from "@/lib/auth/index";
import { signOut } from "@/app/api/auth/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { DeleteChartButton } from "@/components/DeleteChartButton";
import { maxSavedCharts } from "@/lib/features";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) redirect("/auth/signin");

  const dbOk = await dbHealthy();
  let charts: Awaited<ReturnType<typeof getHoroscopes>> = [];
  let loadError: string | null = null;
  try {
    charts = await getHoroscopes(session.userId);
  } catch (e) {
    loadError = e instanceof Error ? e.message : "Could not load saved charts";
    console.error("dashboard getHoroscopes:", loadError);
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-text-muted">
            Signed in as {session.email} · {session.role} tier
            {" · "}
            {charts.length}/{maxSavedCharts(session.role)} saved
          </p>
        </div>
        <div className="flex items-center gap-4">
          <form
            action={async () => {
              "use server";
              await signOut({ redirectTo: "/vedicastro" });
            }}
          >
            <button
              type="submit"
              className="text-sm text-text-muted hover:text-text-main transition-colors"
            >
              Sign out
            </button>
          </form>
          <Link
            href="/vedicastro"
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-[#1a1206] hover:bg-accent-strong transition-colors"
          >
            Cast a chart
          </Link>
        </div>
      </div>

      {!dbOk && (
        <div className="rounded-xl border border-warning/40 bg-warning/5 p-4 text-sm text-warning mb-6">
          Database not connected — charts won&apos;t be saved. Set DATABASE_URL in your environment.
        </div>
      )}

      {loadError && (
        <div className="rounded-xl border border-danger/40 bg-danger/5 p-4 text-sm text-danger mb-6">
          {loadError}
        </div>
      )}

      <div className="rounded-2xl border border-hairline bg-card">
        <div className="px-5 py-4 border-b border-hairline">
          <h2 className="font-medium">Saved charts</h2>
        </div>
        {charts.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            <p>No saved charts yet.</p>
            <Link href="/vedicastro" className="mt-2 inline-block text-accent hover:underline">
              Cast your first chart →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-hairline">
            {charts.map((c) => {
              const meta = (c.chart_data.meta ?? {}) as Record<string, unknown>;
              const birthDt =
                typeof meta.birth_datetime === "string" ? meta.birth_datetime : "";
              const birthDate = birthDt.slice(0, 10);
              const birthTime = birthDt.slice(11, 16);
              const href = `/vedicastro?name=${encodeURIComponent(c.name)}&date=${birthDate}&time=${birthTime}&lat=${meta.birth_lat ?? ""}&lon=${meta.birth_lon ?? ""}&tz=${meta.birth_tz ?? ""}`;

              return (
              <div
                key={c.id}
                className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-[color-mix(in_srgb,var(--color-accent)_3%,transparent)] transition-colors"
              >
                <Link href={href} className="min-w-0 flex-1">
                  <div className="text-sm font-medium">{c.name}</div>
                  <div className="mt-0.5 text-xs text-text-muted flex flex-wrap gap-x-2 gap-y-0.5">
                    {birthDate && (
                      <span>
                        Born {birthDate}
                        {birthTime ? ` · ${birthTime}` : ""}
                      </span>
                    )}
                    <span className="text-text-muted/70">
                      Saved {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </Link>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-text-muted font-mono">{c.id.slice(0, 8)}</span>
                  <DeleteChartButton id={c.id} />
                </div>
              </div>
            );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
