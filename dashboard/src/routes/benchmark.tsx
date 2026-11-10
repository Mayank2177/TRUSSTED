import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, BarChart3, ChevronDown, ChevronUp, Info, Link2Off } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { EvidenceStamp, PageHeader, StatusBadge } from "@/components/evidence";
import { scenarios, scenarioResultLabel } from "@/lib/evidence-data";

export const Route = createFileRoute("/benchmark")({
  head: () => ({ meta: [
    { title: "Benchmark · Trussted" },
    { name: "description", content: "Inspect example benchmark scenarios, confidence intervals, false-block rates, and failed outcomes in Trussted." },
    { property: "og:title", content: "Benchmark · Trussted" },
    { property: "og:description", content: "Illustrative scenario results, sample counts, confidence intervals, and a visible failed case." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary" },
  ] }),
  component: BenchmarkPage,
});

function ComparisonBar({ baseline, trussted }: { baseline: { value: number; ciLow: number; ciHigh: number }; trussted: { value: number; ciLow: number; ciHigh: number } }) {
  return <div className="comparison-chart" role="img" aria-label={`Baseline ${baseline.value}% with 95% confidence interval ${baseline.ciLow} to ${baseline.ciHigh} percent; Trussted ${trussted.value}% with 95% confidence interval ${trussted.ciLow} to ${trussted.ciHigh} percent.`}>
    {([ ["Baseline", baseline, "baseline-bar"], ["Trussted", trussted, "trussted-bar"] ] as const).map(([label, data, tone]) => <div className="bar-line" key={label}>
      <span className="bar-label">{label}</span>
      <div className="bar-track"><span className={`bar-fill ${tone}`} style={{ width: `${data.value}%` }} /><span className="bar-whisker" style={{ left: `${data.ciLow}%`, width: `${data.ciHigh - data.ciLow}%` }} /></div>
      <span className="bar-value">{data.value}%</span>
    </div>)}
    <div className="axis-ticks" aria-hidden="true"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
  </div>;
}

function ScenarioDetails({ id }: { id: string }) {
  const [open, setOpen] = useState(false);
  const scenario = scenarios.find((item) => item.id === id);
  if (!scenario) return null;
  return <div className="scenario-detail">
    <Button variant="ghost" className="detail-trigger" aria-expanded={open} aria-controls={`detail-${id}`} onClick={() => setOpen(!open)}>
      {open ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}{open ? "Hide evidence" : "Evidence details"}
    </Button>
    {open ? <div id={`detail-${id}`} className="detail-panel">
      <ComparisonBar baseline={scenario.baseline} trussted={scenario.trussted} />
      <p className="detail-note"><Info aria-hidden="true" /> Values are percentages with 95% Wilson confidence intervals. Each scenario has n={scenario.n}. Example values only.</p>
    </div> : null}
  </div>;
}

function BenchmarkPage() {
  const failed = scenarios.filter((scenario) => !scenario.mitigated);
  return <div>
    <PageHeader eyebrow="EVALUATION SET 2026.11" title="Benchmark" description="Compare baseline and Trussted outcomes by scenario. Sample counts and confidence intervals stay attached to every percentage." actions={<EvidenceStamp />} />
    <section className="benchmark-overview">
      <div className="benchmark-overview-icon"><BarChart3 aria-hidden="true" /></div>
      <div><p className="eyebrow">SAMPLE SUMMARY</p><h2>6 scenarios · n=40 each · 240 observations total</h2><p>Each scenario shows ASR outcome, uncertainty interval, decision, and false-block rate.</p></div>
    </section>
    <section className="failed-notice" aria-labelledby="failed-heading">
      <AlertTriangle aria-hidden="true" />
      <div><h2 id="failed-heading">{failed.length} scenario not mitigated</h2><p>{failed.map((scenario) => `${scenario.id} · ${scenario.type}`).join("; ")}</p></div>
    </section>
    <section className="scenario-section" aria-labelledby="scenario-heading">
      <div className="section-heading-row">
        <div><h2 id="scenario-heading" className="section-title">Scenario results</h2><p className="section-subtitle">Each row includes n and 95% confidence intervals for both outcome rates.</p></div>
        <span className="scenario-count">{scenarios.length} SCENARIOS</span>
      </div>
      <div className="scenario-list">
        {scenarios.map((scenario) => <article className={`scenario-row${scenario.mitigated ? "" : " scenario-row-failed"}`} key={scenario.id}>
          <div className="scenario-main">
            <span className="scenario-id mono-text">{scenario.id}</span>
            <div className="scenario-name-wrap"><h3>{scenario.type}</h3>{!scenario.mitigated ? <span className="failed-label"><AlertTriangle aria-hidden="true" /> Not mitigated</span> : null}</div>
          </div>
          <div className="scenario-measure"><span className="scenario-measure-label">Baseline ASR</span><span className="scenario-measure-value">{scenario.baseline.value}% <small>n={scenario.n} · CI {scenario.baseline.ciLow}–{scenario.baseline.ciHigh}%</small></span></div>
          <div className="scenario-measure"><span className="scenario-measure-label">Trussted ASR</span><span className="scenario-measure-value">{scenario.trussted.value}% <small>n={scenario.n} · CI {scenario.trussted.ciLow}–{scenario.trussted.ciHigh}%</small></span></div>
          <div className="scenario-measure"><span className="scenario-measure-label">False-block</span><span className="scenario-measure-value">{scenario.falseBlock}% <small>n={scenario.n}</small></span></div>
          <div className="scenario-result"><span className="scenario-measure-label">Decision</span><StatusBadge status={scenario.status} /><span className={`result-label${scenario.mitigated ? " result-pass" : " result-fail"}`}>{scenarioResultLabel(scenario)}</span></div>
          <ScenarioDetails id={scenario.id} />
        </article>)}
      </div>
    </section>
    <section className="reason-code-section" aria-labelledby="reason-heading">
      <p className="eyebrow">REASON CODE REFERENCE</p>
      <h2 id="reason-heading" className="section-title">A reason code, in plain language</h2>
      <div className="reason-row"><code className="mono-text">FACT_CONFLICT_HIGH</code><p>Price or specification on the page disagrees with the reference source.</p></div>
    </section>
    <section id="limitations" className="limitations-section" aria-labelledby="limitations-heading">
      <p className="eyebrow">SCOPE &amp; LIMITATIONS</p>
      <h2 id="limitations-heading" className="section-title">What this sample does not establish</h2>
      <ul className="limitations-list">
        <li><Info aria-hidden="true" /> All runs, counts, intervals, source records, and outcomes on these screens are example data, not measured production results.</li>
        <li><Info aria-hidden="true" /> The benchmark does not establish performance outside the six illustrative scenarios shown here.</li>
        <li><Link2Off aria-hidden="true" /> Receipt event digests are example strings; no cryptographic verification or public-key validation is connected.</li>
        <li><Info aria-hidden="true" /> Shopping listings and prices are illustrative, not current offers from a connected store.</li>
      </ul>
    </section>
  </div>;
}