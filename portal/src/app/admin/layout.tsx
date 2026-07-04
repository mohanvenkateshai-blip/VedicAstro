import { requireSession } from "@/lib/auth/index";
import { AdminNav } from "@/components/admin/AdminNav";

/** Gates the whole /admin section to admins and renders the shared admin sub-nav
 *  so tools (Console / System health / Knowledge graph) are one click apart. */
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  await requireSession("admin");
  return (
    <>
      <AdminNav />
      {children}
    </>
  );
}
