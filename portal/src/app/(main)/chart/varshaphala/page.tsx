import Link from "next/link";
import { loadChartFromSearchParams } from "@/lib/load-chart";
import { getSession, hasAtLeast } from "@/lib/auth/index";
import { Card } from "@/components/ui/Card";
import { VarshaphalaPanel } from "@/components/explorers/VarshaphalaPanel";

type SP = Record<string, string | string[] | undefined>;

export default async function VarshaphalaPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const session = await getSession();
  const sp = await searchParams;
  const { chart, error } = await loadChartFromSearchParams(sp);

  const isPro = session ? hasAtLeast(session.role, "pro") : true; // allow when auth not configured

  // Preserve birth params so sign-in / upgrade keeps the current chart context
  const qs = Object.entries(sp)
    .filter(([, v]) => v != null)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  const returnPath = qs ? `/chart/varshaphala?${qs}` : "/chart/varshaphala";
  const signInHref = `/auth/signin?callbackUrl=${encodeURIComponent(returnPath)}`;

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h2 className="font-[family-name:var(--font-display)] font-semibold text-lg">
          Varshaphala
        </h2>
        <p className="text-sm text-text-muted mt-1">
          Solar return analysis · {session?.role ?? "free"} tier
        </p>
      </Card>

      {!isPro ? (
        <Card className="p-6 border border-amber-500/30 bg-amber-500/5">
          <div className="text-sm font-medium">Solar Return is a Pro feature</div>
          <p className="text-sm text-text-muted mt-2">
            Upgrade to Pro to access Tajika solar return charts, Muntha, Patyayini dasha, Harsha Bala, and annual predictions.
          </p>
          <div className="mt-3">
            <Link
              href={signInHref}
              className="inline-flex items-center rounded-lg border border-amber-500/40 px-3 py-1.5 text-sm hover:bg-amber-500/10"
            >
              Sign in with Pro account
            </Link>
          </div>
          <p className="text-xs text-text-muted mt-3">
            Or contact support to upgrade your tier.
          </p>
        </Card>
      ) : (
        <>
          {error ? (
            <Card className="p-6 border-danger/40">
              <p className="text-sm text-danger">{error}</p>
            </Card>
          ) : null}
          {chart ? <VarshaphalaPanel chart={chart} /> : null}
        </>
      )}
    </div>
  );
}
