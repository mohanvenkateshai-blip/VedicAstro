import { clsx } from "clsx";

/** User avatar — renders the OAuth profile image if present, else initials on a
 *  tinted disc. Hook-free so it works in both server and client components. */
export function Avatar({
  name,
  email,
  image,
  size = "md",
  className,
}: {
  name?: string | null;
  email?: string | null;
  image?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const dim =
    size === "sm" ? "h-7 w-7 text-[11px]" : size === "lg" ? "h-12 w-12 text-base" : "h-9 w-9 text-sm";

  const seed = (name || email || "?").trim();
  const initials = seed
    .split(/\s+/)
    .slice(0, 2)
    .map((s) => s[0])
    .join("")
    .toUpperCase() || "?";

  if (image) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- external OAuth avatar, no Image config
      <img
        src={image}
        alt={name || email || "User"}
        referrerPolicy="no-referrer"
        className={clsx(dim, "rounded-full object-cover ring-1 ring-hairline", className)}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={clsx(
        dim,
        "grid place-items-center rounded-full bg-primary/10 font-medium text-primary ring-1 ring-hairline select-none",
        className,
      )}
    >
      {initials}
    </span>
  );
}
