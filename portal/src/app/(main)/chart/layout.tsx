import { ChartSidebar } from "@/components/ChartSidebar";
import { BirthForm } from "@/components/BirthForm";

export default function ChartLayout({ children }: { children: React.ReactNode }) {
  const defaults = {
    name: "Mohan", date: "1975-04-22", time: "19:15", place: "Mysore, IN",
    lat: "12.2958", lon: "76.6394", tz: "5.5",
  };
  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="flex gap-8">
        <aside className="shrink-0 hidden lg:block pt-2 w-56">
          <ChartSidebar />
        </aside>
        <main className="flex-1 min-w-0">
          <BirthForm defaults={defaults} />
          <div className="mt-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
