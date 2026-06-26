import { Card } from "@/components/ui/Card";
import { KootaMatcher } from "@/components/explorers/KootaMatcher";

export default function CompatibilityPage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      <Card className="p-5"><h2 className="font-semibold text-lg">Koota Matching — Compatibility</h2></Card>
      <KootaMatcher />
    </div>
  );
}
