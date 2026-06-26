import { Card } from "@/components/ui/Card";
import { SpecialPointsPanel } from "@/components/explorers/SpecialPointsPanel";
export default function Page() { return (<div className="space-y-6"><Card className="p-5"><h2 className="font-semibold text-lg">Special Points</h2></Card><SpecialPointsPanel chart={undefined as any} /></div>); }
