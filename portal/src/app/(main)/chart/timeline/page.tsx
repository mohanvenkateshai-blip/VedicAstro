import { CalendarDays, FlaskConical } from "lucide-react";
import { PersonTimeline } from "@/components/timeline/PersonTimeline";
import { Card } from "@/components/ui/Card";
import { birthQueryString } from "@/lib/birth-params";
import { getPersonTimeline, getPersonTimelineMilestone } from "@/lib/cvce";
import { loadChartFromSearchParams } from "@/lib/load-chart";
import { timelineSubjectId } from "@/lib/timeline-subject";
import { resolveChartOwner } from "@/lib/chart-owner";

export const maxDuration = 60;

type SP = Record<string, string | string[] | undefined>;
const one = (value: string | string[] | undefined) => Array.isArray(value) ? value[0] : value;

export default async function TimelinePage({ searchParams }: { searchParams: Promise<SP> }) {
  const params = await searchParams;
  const { chart, birth, defaults, error } = await loadChartFromSearchParams(params);
  let timeline = null;
  let initialDetail = null;
  let timelineError: string | null = null;
  const owner = await resolveChartOwner();
  const subjectId = chart && owner ? timelineSubjectId(birth, owner) : null;

  if (chart && subjectId) {
    try {
      timeline = await getPersonTimeline(birth, subjectId);
      const milestoneId = one(params.milestone);
      if (milestoneId) {
        initialDetail = await getPersonTimelineMilestone(birth, milestoneId, subjectId).catch(() => null);
      }
    } catch (caught) {
      timelineError = caught instanceof Error ? caught.message : "Could not load the person timeline.";
    }
  } else if (chart) {
    timelineError = "A private timeline owner could not be established. Reload the page and try again.";
  }

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden bg-aurora p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-accent/15 p-2.5 text-accent"><CalendarDays className="size-5" /></div>
          <div><h1 className="text-xl font-semibold">Person Timeline</h1><p className="mt-1 max-w-3xl text-sm leading-relaxed text-text-muted">Compare what actually happened in this person&apos;s life with timing research from the chart. On first open you will see dasha periods and yoga activation candidates — not life events until you add them.</p></div>
        </div>
      </Card>

      {(error || timelineError) && <Card className="border-danger/40 p-5"><p className="text-sm font-semibold text-danger">Timeline unavailable</p><p className="mt-1 text-xs text-text-muted">{error ?? timelineError}</p></Card>}

      {!chart && !error && <Card className="grid place-items-center p-10 text-center"><FlaskConical className="size-7 text-accent" /><h2 className="mt-3 text-base font-semibold">Enter this person’s birth details above</h2><p className="mt-1 max-w-lg text-sm text-text-muted">The timeline is calculated for the active chart. Add observed milestones after the chart loads to make this workspace personal.</p></Card>}

      {chart && timeline && subjectId && <PersonTimeline timeline={timeline} birth={birth} subjectId={subjectId} birthQuery={birthQueryString(defaults)} initialMilestoneId={one(params.milestone)} initialDetail={initialDetail} />}
    </div>
  );
}
