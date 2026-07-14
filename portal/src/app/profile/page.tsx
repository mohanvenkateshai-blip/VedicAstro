import Link from "next/link";
import { requireSession, getUser, countHoroscopes } from "@/lib/auth/index";
import { AvatarUpload } from "@/components/masthead/AvatarUpload";
import { ProfileNameForm } from "@/components/masthead/ProfileNameForm";

export const dynamic = "force-dynamic";

const ROLE_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  premium: "Premium",
  admin: "Admin",
};

export default async function ProfilePage() {
  const session = await requireSession();
  const [user, charts] = await Promise.all([
    getUser(session.userId),
    countHoroscopes(session.userId).catch(() => 0),
  ]);

  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "—";

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent font-medium">Account</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight font-serif">Profile</h1>
        </div>
        <Link href="/settings" className="text-sm text-text-muted hover:text-text-main shrink-0">
          Settings →
        </Link>
      </div>

      <div className="rounded-2xl border border-hairline bg-card p-6">
        <div className="flex items-center gap-4">
          <AvatarUpload name={session.name} email={session.email} image={session.image} />
          <div className="min-w-0">
            <p className="truncate text-lg font-medium">{session.name || "Unnamed seeker"}</p>
            <p className="truncate text-sm text-text-muted">{session.email}</p>
          </div>
          <span className="ml-auto rounded-full border border-accent/40 px-2.5 py-1 text-xs font-medium text-accent">
            {ROLE_LABEL[session.role] ?? session.role}
          </span>
        </div>

        <div className="mt-6 border-t border-hairline pt-6">
          <ProfileNameForm initialName={session.name ?? ""} />
        </div>

        <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-hairline pt-6 text-sm">
          <div>
            <dt className="text-text-muted">Member since</dt>
            <dd className="mt-0.5 font-medium">{memberSince}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Saved charts</dt>
            <dd className="mt-0.5 font-medium">{charts}</dd>
          </div>
        </dl>
      </div>

      <p className="mt-4 text-center text-xs text-text-muted">
        Saved charts are isolated to your account. Encryption coverage and legacy-data details are in{" "}
        <Link href="/settings" className="text-accent hover:underline">
          Settings
        </Link>{" "}
        for appearance and account options.
      </p>
    </div>
  );
}
