export default function AuthError() {
  return (
    <div className="mx-auto max-w-md px-6 py-24">
      <div className="rounded-2xl border border-hairline bg-card p-8 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Authentication Error</h1>
        <p className="mt-2 text-sm text-text-muted">
          Something went wrong during sign in. Please try again.
        </p>
        <a href="/auth/signin" className="mt-6 inline-block text-sm text-accent hover:underline">
          ← Back to sign in
        </a>
      </div>
    </div>
  );
}
