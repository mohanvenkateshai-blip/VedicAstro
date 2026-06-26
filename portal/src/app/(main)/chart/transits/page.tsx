import { Card } from "@/components/ui/Card";
import AnimatedTransitEngine from "@/components/explorers/AnimatedTransitEngine";
import { GraphicalEphemeris } from "@/components/explorers/GraphicalEphemeris";
export default function Page() { return (<div className="space-y-6"><Card className="p-5"><h2 className="font-semibold text-lg">Transits</h2></Card><AnimatedTransitEngine /><GraphicalEphemeris chart={undefined as any} /></div>); }
