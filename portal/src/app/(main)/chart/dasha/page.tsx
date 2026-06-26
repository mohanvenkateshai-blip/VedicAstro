import { Card } from "@/components/ui/Card";
import { DashaDeepTree } from "@/components/explorers/DashaDeepTree";
import { AllDashasPanel } from "@/components/explorers/AllDashasPanel";
export default function Page() { return (<div className="space-y-6"><Card className="p-5"><h2 className="font-semibold text-lg">Dasha Timeline</h2></Card><DashaDeepTree /><AllDashasPanel /></div>); }
