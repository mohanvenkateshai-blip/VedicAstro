import { getSession } from "@/lib/auth";
import { getHoroscopes, dbHealthy } from "@/lib/auth/index";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) redirect("/auth/signin");

  const dbOk = await dbHealthy();
  const charts = session ? await getHoroscopes(session.userId).catch(() => []) : [];

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-text-muted">
            Signed in as {session.email} · {session.role} tier
          </p>
        </div>
        <Link
          href="/vedicastro"
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-[#1a1206] hover:bg-accent-strong transition-colors"
        >
          Cast a chart
        </Link>
      </div>

      {!dbOk && (
        <div className="rounded-xl border border-warning/40 bg-warning/5 p-4 text-sm text-warning mb-6">
          Database not connected — charts won&apos;t be saved. Set DATABASE_URL in your environment.
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
            {charts.map((c) => (
              <Link
                key={c.id}
                href={`/vedicastro?name=${encodeURIComponent(c.name)}&date=${(c.chart_data.meta as any)?.birth_datetime?.slice(0, 10) ?? ""}&time=${(c.chart_data.meta as any)?.birth_datetime?.slice(11, 16) ?? ""}&lat=${(c.chart_data.meta as any)?.birth_lat ?? ""}&lon=${(c.chart_data.meta as any)?.birth_lon ?? ""}&tz=${(c.chart_data.meta as any)?.birth_tz ?? ""}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-[color-mix(in_srgb,var(--color-accent)_3%,transparent)] transition-colors"
              >
                <div>
                  <span className="text-sm font-medium">{c.name}</span>
                  <span className="ml-3 text-xs text-text-muted">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                </div>
                <span className="text-xs text-text-muted font-mono">{c.id.slice(0, 8)}</span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
