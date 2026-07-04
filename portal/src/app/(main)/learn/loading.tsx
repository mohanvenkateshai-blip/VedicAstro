import { BookOpen } from "lucide-react";

/** Instant navigation feedback for the Learn route. The library page fetches the
 *  whole corpus (slow), and without this skeleton a click on "Learn" showed no
 *  feedback for several seconds — it read as non-functional. Next renders this
 *  immediately on navigation while the page's data resolves. */
export default function LearnLoading() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 lg:py-14 animate-pulse">
      {/* Hero */}
      <div className="max-w-3xl mb-12">
        <div className="inline-flex items-center gap-2 rounded-full border border-hairline px-3 py-1 text-xs tracking-[0.08em] text-text-muted mb-4">
          <BookOpen className="w-3.5 h-3.5" /> ŚĀSTRA SAṄGRAHA
        </div>
        <div className="h-12 lg:h-14 w-4/5 rounded-lg bg-hairline/50 mb-4" />
        <div className="h-5 w-full max-w-2xl rounded bg-hairline/40" />
      </div>

      {/* Search bar */}
      <div className="mb-10">
        <div className="h-12 w-full max-w-2xl rounded-2xl border border-hairline bg-card" />
      </div>

      {/* Book grid skeleton */}
      <div className="flex items-end justify-between mb-6">
        <div>
          <div className="h-8 w-48 rounded bg-hairline/50" />
          <div className="mt-2 h-4 w-64 rounded bg-hairline/40" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex flex-col rounded-2xl border border-hairline bg-card p-7">
            <div className="h-7 w-3/4 rounded bg-hairline/50" />
            <div className="mt-2 h-4 w-1/2 rounded bg-hairline/40" />
            <div className="mt-6 pt-5 border-t border-hairline flex items-center justify-between">
              <div className="h-3 w-24 rounded bg-hairline/40" />
              <div className="h-3 w-16 rounded bg-hairline/40" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
