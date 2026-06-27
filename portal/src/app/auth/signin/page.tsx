import { signIn, auth } from "@/app/api/auth/auth";
import { redirect } from "next/navigation";
import { isAuthConfigured } from "@/lib/auth-config";

type SP = { callbackUrl?: string };

export default async function SignIn({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { callbackUrl } = await searchParams;
  const redirectTo = callbackUrl?.startsWith("/") ? callbackUrl : "/dashboard";

  if (!isAuthConfigured()) {
    return (
      <div className="mx-auto max-w-md px-6 py-24">
        <div className="rounded-2xl border border-warning/40 bg-warning/5 p-8 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Sign-in unavailable</h1>
          <p className="mt-2 text-sm text-text-muted">
            Google OAuth is not configured on this deployment. Set AUTH_SECRET,
            AUTH_GOOGLE_ID, and AUTH_GOOGLE_SECRET in the environment.
          </p>
          <a href="/vedicastro" className="mt-6 inline-block text-sm text-accent hover:underline">
            ← Continue without signing in
          </a>
        </div>
      </div>
    );
  }

  const session = await auth();
  if (session?.user) redirect(redirectTo);

  return (
    <div className="mx-auto max-w-md px-6 py-24">
      <div className="rounded-2xl border border-hairline bg-card p-8">
        <h1 className="text-2xl font-semibold tracking-tight text-center">Sign in to VedicAstro</h1>
        <p className="mt-2 text-sm text-text-muted text-center">
          Save your charts, track dashas, and get personalised insights.
        </p>
        <form
          action={async () => {
            "use server";
            await signIn("google", { redirectTo });
          }}
          className="mt-6"
        >
          <button
            type="submit"
            className="w-full inline-flex items-center justify-center gap-3 rounded-xl border border-hairline px-6 py-3 text-sm font-medium hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,transparent)] transition-colors"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
        </form>
      </div>
    </div>
  );
}
