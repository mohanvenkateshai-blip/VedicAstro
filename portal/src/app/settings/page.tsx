import Link from "next/link";
import { requireSession } from "@/lib/auth/index";
import { ThemePicker } from "@/components/masthead/ThemePicker";
import { SignOutButton } from "@/components/masthead/SignOutButton";

export const dynamic = "force-dynamic";

const ROLE_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  premium: "Premium",
  admin: "Admin",
};

function Section({
  title,
  desc,
  children,
}: {
  title: string;
  desc?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-hairline bg-card p-6">
      <h2 className="text-sm font-semibold">{title}</h2>
      {desc && <p className="mt-1 text-xs text-text-muted">{desc}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default async function SettingsPage() {
  const session = await requireSession();

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-accent font-medium">Account</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight font-serif">Settings</h1>
        </div>
        <Link href="/profile" className="text-sm text-text-muted hover:text-text-main shrink-0">
          ← Profile
        </Link>
      </div>

      <div className="space-y-4">
        <Section title="Appearance" desc="Theme follows you across devices while signed in.">
          <ThemePicker signedIn size="md" />
        </Section>

        <Section title="Notifications" desc="Where product updates and chart events appear.">
          <p className="text-sm text-text-muted">
            In-app notifications are on. Fine-grained delivery preferences are coming soon.
          </p>
        </Section>

        <Section title="Saved-chart privacy" desc="How sensitive birth details are protected.">
          <div className="space-y-2 text-sm text-text-muted">
            <p>
              New server-saved charts are accepted only when authenticated encryption is configured.
              Saved charts are scoped to your account; guest charts are scoped to this browser.
            </p>
            <p>
              Charts saved before encrypted storage was enabled may remain in the legacy plaintext
              format until the deployment migration is completed. Birth details in copied URLs or
              browser history are outside server-side saved-chart encryption.
            </p>
          </div>
        </Section>

        <Section title="Account">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-text-muted">Email</dt>
              <dd className="mt-0.5 truncate font-medium">{session.email}</dd>
            </div>
            <div>
              <dt className="text-text-muted">Plan</dt>
              <dd className="mt-0.5 font-medium">{ROLE_LABEL[session.role] ?? session.role}</dd>
            </div>
          </dl>
          <div className="mt-5 border-t border-hairline pt-5">
            <SignOutButton />
          </div>
        </Section>
      </div>
    </div>
  );
}
