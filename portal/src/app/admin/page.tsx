import Link from "next/link";
import { requireSession } from "@/lib/auth/index";
import { Activity, ShieldCheck } from "lucide-react";

export const dynamic = "force-dynamic";

function AdminCard({
  href,
  title,
  desc,
  icon,
}: {
  href: string;
  title: string;
  desc: string;
  icon: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group rounded-2xl border border-hairline bg-card p-5 transition-colors hover:border-accent/40"
    >
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </span>
        <h2 className="text-base font-medium">{title}</h2>
      </div>
      <p className="mt-3 text-sm text-text-muted">{desc}</p>
      <span className="mt-3 inline-block text-sm text-accent group-hover:underline">Open →</span>
    </Link>
  );
}

export default async function AdminHome() {
  const session = await requireSession("admin");

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-accent font-medium">
        <ShieldCheck size={14} /> Admin
      </div>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight font-serif">Admin console</h1>
      <p className="mt-2 text-sm text-text-muted">
        Operational tools — restricted to administrators. Signed in as{" "}
        <span className="font-medium text-text-main">{session.email}</span>.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <AdminCard
          href="/admin/health"
          title="System health"
          desc="Live per-subsystem probes from CVCE — engine, knowledge, Supabase, memory."
          icon={<Activity size={18} />}
        />
      </div>
    </div>
  );
}
