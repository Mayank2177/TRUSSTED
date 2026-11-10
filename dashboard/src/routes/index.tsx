import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight, Clock3, Download, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MetricCard, PageHeader, StatusBadge } from "@/components/evidence";
import { recentRuns, runMetrics } from "@/lib/evidence-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Runs · Trussted" },
      { name: "description", content: "Review illustrative decision runs, evidence, sample sizes, and scenario outcomes in Trussted." },
      { property: "og:title", content: "Runs · Trussted" },
      { property: "og:description", content: "Illustrative decision runs with sample sizes, uncertainty, and scenario outcomes." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: RunsPage,
});

function RunsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="DECISION EVIDENCE"
        title="Runs"
        description="An inspectable record of what was tested, what happened, and where the evidence is uncertain."
        actions={<Button variant="outline" className="min-h-11" aria-label="Export sample run summary"><Download /> Export summary</Button>}
      />

      <section aria-labelledby="overview-heading" className="section-block">
        <div className="section-heading-row">
          <div>
            <h2 id="overview-heading" className="section-title">Latest benchmark snapshot</h2>
            <p className="section-subtitle">Trussted · evaluation set 2026.11 · illustrative sample</p>
          </div>
          <span className="sample-stamp"><FlaskConical aria-hidden="true" /> EXAMPLE RESULTS</span>
        </div>
        <div className="metric-grid">
          {runMetrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
        </div>
      </section>

      <section aria-labelledby="runs-heading" className="section-block">
        <div className="section-heading-row">
          <div>
            <h2 id="runs-heading" className="section-title">Recent runs</h2>
            <p className="section-subtitle">Failures stay visible alongside completed runs.</p>
          </div>
          <Button variant="ghost" asChild className="min-h-11"><Link to="/benchmark">Open benchmark <ArrowUpRight aria-hidden="true" /></Link></Button>
        </div>
        <div className="run-list">
          {recentRuns.map((run) => (
            <article className={`run-row${run.failed ? " run-row-failed" : ""}`} key={run.id}>
              <div className="run-main">
                <span className={`run-state-dot${run.failed ? " run-state-dot-failed" : ""}`} aria-hidden="true" />
                <div className="run-title-wrap">
                  <h3 className="run-title">{run.title}</h3>
                  <p className="run-id mono-text">{run.id}</p>
                </div>
              </div>
              <div className="run-meta"><Clock3 aria-hidden="true" /><span>{run.date}</span></div>
              <StatusBadge status={run.status} />
              <div className="run-result">{run.result}</div>
            </article>
          ))}
        </div>
      </section>

      <section className="latest-evidence" aria-labelledby="evidence-heading">
        <div className="evidence-number">01</div>
        <div className="evidence-body">
          <p className="eyebrow">LATEST EVIDENCE</p>
          <h2 id="evidence-heading">One scenario was not mitigated.</h2>
          <p>Scenario S6 returned a BLOCK decision, but the outcome did not meet the benchmark threshold. It remains in the results.</p>
        </div>
        <Button asChild variant="outline" className="min-h-11"><Link to="/benchmark">Review S6 <ArrowUpRight aria-hidden="true" /></Link></Button>
      </section>
    </div>
  );
}