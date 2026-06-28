import Link from "next/link";
import { DashboardTable } from "@/components/DashboardTable";

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-text-muted">
            Saved charts — stored locally in this browser
          </p>
        </div>
        <Link
          href="/chart"
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-[#1a1206] hover:bg-accent-strong transition-colors"
        >
          Cast a chart
        </Link>
      </div>

      <DashboardTable />
    </div>
  );
}
