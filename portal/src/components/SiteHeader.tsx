"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";
import { ButtonLink } from "./ui/Button";

import type { Role } from "@/lib/auth/types";

export function SiteHeader({ signedIn = false, role }: { signedIn?: boolean; role?: Role }) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-[color-mix(in_srgb,var(--color-background)_85%,transparent)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5" aria-label="VedicShastra AI home">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-fg font-serif text-lg" aria-hidden="true">ॐ</span>
          <span className="font-semibold tracking-tight">
            VedicShastra <span className="text-accent">AI</span>
          </span>
        </Link>
        <nav aria-label="Main navigation" className="flex items-center gap-1">
          <Link
            href="/compatibility"
            aria-current={pathname === "/compatibility" ? "page" : undefined}
            className="hidden sm:inline px-3 py-2 text-sm text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg"
          >
            Compatibility
          </Link>
          <Link
            href="/muhurta"
            aria-current={pathname === "/muhurta" ? "page" : undefined}
            className="hidden sm:inline px-3 py-2 text-sm text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg"
          >
            Muhūrta
          </Link>
          <Link
            href="/learn/nakshatras"
            aria-current={pathname?.startsWith("/learn") ? "page" : undefined}
            className="hidden sm:inline px-3 py-2 text-sm text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg"
          >
            Learn
          </Link>
          <Link
            href="/dashboard"
            aria-current={pathname === "/dashboard" ? "page" : undefined}
            className="hidden sm:inline px-3 py-2 text-sm text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg"
          >
            Dashboard
          </Link>
          {role === "admin" && (
            <Link
              href="/admin/knowledge"
              aria-current={pathname?.startsWith("/admin") ? "page" : undefined}
              className="hidden sm:inline px-3 py-2 text-sm text-text-muted hover:text-text-main transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded-lg"
            >
              Knowledge
            </Link>
          )}
          <ThemeToggle />
          <ButtonLink href="/chart" variant="primary" className="!px-4 !py-2 text-sm">
            Cast a chart
          </ButtonLink>
        </nav>
      </div>
    </header>
  );
}
