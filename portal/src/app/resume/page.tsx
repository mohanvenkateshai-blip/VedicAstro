import { redirect } from "next/navigation";
import { requireSession } from "@/lib/auth/index";

export const dynamic = "force-dynamic";

/** Post-login landing: bounce the user to the last page they were on. */
export default async function ResumePage() {
  const session = await requireSession();
  const target =
    session.lastPath && session.lastPath.startsWith("/") ? session.lastPath : "/dashboard";
  redirect(target);
}
