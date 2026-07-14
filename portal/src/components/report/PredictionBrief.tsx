import { Card } from "@/components/ui/Card";
import type { ForecastV2ReleasedResponse } from "@/lib/types";

function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

function Probability({ forecast }: { forecast: ForecastV2ReleasedResponse }) {
  const { claim } = forecast;
  if (claim.probability_status === "calibrated" && claim.forecast_probability != null) {
    return <>{Math.round(claim.forecast_probability * 100)}% calibrated probability</>;
  }
  if (claim.probability_status === "uncalibrated_signal") {
    return <>Traditional signal only — not an empirical probability</>;
  }
  return <>No empirical probability is available</>;
}

function EvidenceList({ label, ids }: { label: string; ids: string[] }) {
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-text-muted">{label}</h4>
      {ids.length ? (
        <ul className="mt-1 list-disc space-y-1 pl-5 text-sm" aria-label={label}>
          {ids.map((id) => <li key={id} className="font-mono text-xs">{id}</li>)}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-text-muted">None recorded</p>
      )}
    </div>
  );
}

/** Accessible display for one released, canonical event forecast. */
export function PredictionBrief({ forecast }: { forecast: ForecastV2ReleasedResponse }) {
  const { claim, brief } = forecast;
  const plan = brief.content_plan;
  const abstained = plan.abstention != null;

  return (
    <Card className="space-y-5 p-5" aria-labelledby={`forecast-${brief.claim_id}`}>
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Event-specific forecast
        </p>
        <h3 id={`forecast-${brief.claim_id}`} className="text-lg font-semibold text-text-main">
          {plan.event.text}
        </h3>
        <p className="text-sm leading-relaxed">{brief.concise_sentence}</p>
      </div>

      {abstained ? (
        <p role="status" className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
          {plan.abstention?.text}
        </p>
      ) : null}

      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-text-muted">Exact window</dt>
          <dd className="font-medium">
            <time dateTime={claim.timing.start_on}>{claim.timing.start_on}</time>
            {" to "}
            <time dateTime={claim.timing.end_on}>{claim.timing.end_on}</time>
            {` (${claim.timing.timezone})`}
          </dd>
        </div>
        <div>
          <dt className="text-text-muted">Polarity</dt>
          <dd className="font-medium">{titleCase(claim.polarity)}</dd>
        </div>
        <div>
          <dt className="text-text-muted">Probability status</dt>
          <dd className="font-medium"><Probability forecast={forecast} /></dd>
        </div>
        <div>
          <dt className="text-text-muted">Birth-time stability</dt>
          <dd className="font-medium">{titleCase(claim.birth_time_sensitivity)}</dd>
        </div>
        {claim.base_rate != null ? (
          <div className="sm:col-span-2">
            <dt className="text-text-muted">Observed base rate</dt>
            <dd className="font-medium">
              {Math.round(claim.base_rate * 100)}%
              {claim.base_rate_source ? ` — ${claim.base_rate_source}` : ""}
            </dd>
          </div>
        ) : null}
      </dl>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <EvidenceList label="Supporting evidence" ids={claim.supporting_evidence_ids} />
        <EvidenceList label="Opposing evidence" ids={claim.opposing_evidence_ids} />
      </div>

      <details className="rounded-md border border-hairline p-3">
        <summary className="cursor-pointer text-sm font-medium">Limitations and scope</summary>
        {plan.limitations.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {plan.limitations.map((item) => <li key={item.source_paths.join(".")}>{item.text}</li>)}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-text-muted">No additional limitations recorded.</p>
        )}
      </details>
    </Card>
  );
}
