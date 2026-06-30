import Link from "next/link";
import { requireSession } from "@/lib/auth/index";
import { KnowledgeExplorer } from "@/components/admin/KnowledgeExplorer";

export default async function AdminKnowledgePage() {
  await requireSession("admin");

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent font-medium">Admin</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight font-serif">
            Knowledge graph
          </h1>
          <p className="mt-2 text-sm text-text-muted max-w-xl">
            Explore Graphify output from the private Supabase vault — nodes, links, and corpus
            sources. Not exposed to clients; service-role APIs only.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="text-sm text-text-muted hover:text-text-main transition-colors shrink-0"
        >
          ← Dashboard
        </Link>
      </div>

      <KnowledgeExplorer />

      <p className="text-[10px] text-text-muted font-mono mt-4">
        Portal surfaces ke_version on cvce-backed responses (compatibility, varshaphala, kp, prashna, etc). Probe: /api/cvce/version
      </p>
    </div>
  );
}
