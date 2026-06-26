import Link from "next/link";
import { clsx } from "clsx";

type Variant = "primary" | "accent" | "ghost";

const base =
  "inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-200 active:scale-[0.985] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-primary-fg hover:bg-primary/90 px-6 py-3 min-h-[44px]",
  accent:
    "bg-accent text-accent-fg hover:bg-accent-strong px-6 py-3 min-h-[44px] shadow-sm",
  ghost:
    "text-text-main hover:bg-[color-mix(in_srgb,var(--color-text-main)_8%,transparent)] px-5 py-3 min-h-[44px] border border-hairline",
};

interface CommonProps {
  variant?: Variant;
  className?: string;
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  className,
  children,
  ...rest
}: CommonProps & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={clsx(base, variants[variant], className)} {...rest}>
      {children}
    </button>
  );
}

export function ButtonLink({
  variant = "primary",
  className,
  href,
  children,
}: CommonProps & { href: string }) {
  return (
    <Link href={href} className={clsx(base, variants[variant], className)}>
      {children}
    </Link>
  );
}
