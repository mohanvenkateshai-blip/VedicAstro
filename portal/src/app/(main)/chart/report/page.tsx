import { loadChartFromSearchParams } from "@/lib/load-chart";
import { getReportFacts, CvceError } from "@/lib/cvce";
import { HoroscopeReport } from "@/components/report/HoroscopeReport";

type SP = Record<string, string | string[] | undefined>;

export default async function ReportPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const { defaults, birth, error: chartError } = await loadChartFromSearchParams(
    await searchParams,
  );

  let report = null;
  let reportError: string | null = chartError;

  if (!chartError && birth) {
    try {
      report = await getReportFacts(birth);
    } catch (e) {
      reportError =
        e instanceof CvceError
          ? e.message
          : "Could not load report facts from the engine.";
    }
  }

  return <HoroscopeReport defaults={defaults} report={report} error={reportError} />;
}
