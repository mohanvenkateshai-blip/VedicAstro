import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Muhūrta — VedicShastra AI",
  description: "The full Muhūrta electional analyzer with personal chart integration.",
};

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);

export default async function MuhurtaPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const d = one(sp.d) ?? "";
  const t = one(sp.t) ?? "";
  const la = one(sp.la) ?? "";
  const lo = one(sp.lo) ?? "";
  const tz = one(sp.tz) ?? "";
  const bd = one(sp.bd) ?? "";
  const bt = one(sp.bt) ?? "";
  const bla = one(sp.bl) ?? "";
  const blo = one(sp.bn) ?? "";
  const btz = one(sp.bz) ?? "";

  const hashParams = [
    d && `d=${encodeURIComponent(d)}`,
    t && `t=${encodeURIComponent(t)}`,
    la && `la=${encodeURIComponent(la)}`,
    lo && `lo=${encodeURIComponent(lo)}`,
    tz && `tz=${encodeURIComponent(tz)}`,
    bd && `bd=${encodeURIComponent(bd)}`,
    bt && `bt=${encodeURIComponent(bt)}`,
    bla && `bl=${encodeURIComponent(bla)}`,
    blo && `bn=${encodeURIComponent(blo)}`,
    btz && `bz=${encodeURIComponent(btz)}`,
  ]
    .filter(Boolean)
    .join("&");

  const src = hashParams
    ? `https://muhurtha.uvwx.me#${hashParams}`
    : "https://muhurtha.uvwx.me";

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full">
      {/* External Muhurta (frozen standalone at muhurtha.uvwx.me) uses CVCE/KE knowledge indirectly via prior sync of classical tables.
          No direct live bridge (by design: standalone is untouched). This page passes prefill via hash only. */}
      <iframe
        src={src}
        title="Muhūrta — Celestial Panchang & Electional Analyzer (external; KE v newbooks-v1 indirectly)"
        className="h-full w-full border-0"
        loading="eager"
        allow="clipboard-write"
        data-ke-version="newbooks-v1-indirect"
      />
      <div className="pointer-events-none absolute bottom-1 right-2 rounded bg-black/40 px-1.5 py-0.5 text-[10px] text-neutral-200">
        external muhurtha.uvwx.me • uses KE corpus indirectly
      </div>
    </div>
  );
}
