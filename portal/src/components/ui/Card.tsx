import { clsx } from "clsx";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={clsx(
        // Elevation from color + a crisp hairline, not a soft AI drop-shadow.
        "bg-card text-card-fg border border-hairline rounded-2xl",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
      {children}
    </div>
  );
}
