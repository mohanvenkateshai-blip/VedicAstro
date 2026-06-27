import { Suspense } from "react";
import { ChartSidebar } from "@/components/ChartSidebar";
import { ChartBirthForm } from "@/components/ChartBirthForm";

export default function ChartLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex gap-8">
        <aside className="shrink-0 hidden lg:block pt-2 w-56">
          <Suspense fallback={null}>
            <ChartSidebar />
          </Suspense>
        </aside>
        <main className="flex-1 min-w-0">
          <Suspense
            fallback={
              <div className="rounded-xl border border-hairline p-6 h-64 animate-pulse bg-card" />
            }
          >
            <ChartBirthForm />
          </Suspense>
          <div className="mt-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
