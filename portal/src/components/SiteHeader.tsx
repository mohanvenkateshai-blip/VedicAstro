"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";
import { ButtonLink } from "./ui/Button";
import { GlobalSearch } from "./masthead/GlobalSearch";
import { NotificationBell } from "./masthead/NotificationBell";
import { UserMenu } from "./masthead/UserMenu";
import type { Session } from "@/lib/auth/types";

const NAV = [
  { href: "/compatibility", label: "Compatibility", match: (p: string) => p === "/compatibility" },
  { href: "/muhurta", label: "Muhūrta", match: (p: string) => p === "/muhurta" },
  { href: "/learn", label: "Learn", match: (p: string) => p.startsWith("/learn") },
  { href: "/dashboard", label: "Dashboard", match: (p: string) => p === "/dashboard" },
];

export function SiteHeader({ session }: { session: Session | null }) {
  const pathname = usePathname() ?? "";
  const signedIn = !!session;

  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-[color-mix(in_srgb,var(--color-background)_85%,transparent)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5" aria-label="VedicShastra AI home">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-fg font-serif text-lg" aria-hidden="true">ॐ</span>
          <span className="hidden font-semibold tracking-tight sm:inline">
            VedicShastra <span className="text-accent">AI</span>
          </span>
        </Link>

        <nav aria-label="Main navigation" className="flex items-center gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={item.match(pathname) ? "page" : undefined}
              className="hidden px-3 py-2 text-sm text-text-muted transition-colors hover:text-text-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg sm:inline"
            >
              {item.label}
            </Link>
          ))}
          {session?.role === "admin" && (
            <Link
              href="/admin/knowledge"
              aria-current={pathname.startsWith("/admin") ? "page" : undefined}
              className="hidden px-3 py-2 text-sm text-text-muted transition-colors hover:text-text-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg sm:inline"
            >
              Knowledge
            </Link>
          )}
        </nav>

        <div className="flex items-center gap-2">
          <GlobalSearch />
          {signedIn ? (
            <>
              <NotificationBell />
              <ButtonLink href="/chart" variant="primary" className="hidden !px-4 !py-2 text-sm md:inline-flex">
                Cast a chart
              </ButtonLink>
              <UserMenu session={session} />
            </>
          ) : (
            <>
              <ThemeToggle />
              <Link
                href="/auth/signin"
                className="hidden px-3 py-2 text-sm text-text-muted transition-colors hover:text-text-main sm:inline"
              >
                Sign in
              </Link>
              <ButtonLink href="/chart" variant="primary" className="!px-4 !py-2 text-sm">
                Cast a chart
              </ButtonLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
