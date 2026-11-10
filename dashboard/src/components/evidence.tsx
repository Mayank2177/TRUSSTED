import type { ReactNode } from "react";
import { Check, CircleX, Hand, Info } from "lucide-react";
import type { DecisionStatus, EvidenceMetricData } from "@/lib/evidence-data";
import { formatMetricEvidence } from "@/lib/evidence-data";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="page-title">{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {actions ? <div className="page-header-actions">{actions}</div> : null}
    </header>
  );
}

export function StatusBadge({ status }: { status: DecisionStatus }) {
  const config = {
    ALLOW: { Icon: Check, label: "ALLOW", className: "status-allow" },
    STEP_UP: { Icon: Hand, label: "STEP UP", className: "status-step" },
    BLOCK: { Icon: CircleX, label: "BLOCK", className: "status-block" },
  }[status];
  const { Icon } = config;
  return <span className={`status-badge ${config.className}`}><Icon aria-hidden="true" />{config.label}</span>;
}

export function MetricCard({ metric }: { metric: EvidenceMetricData }) {
  const evidence = formatMetricEvidence(metric);
  if (!evidence) return null;
  return (
    <article className="metric-card">
      <h3 className="metric-label">{metric.label}</h3>
      <p className="metric-value">{metric.value.toFixed(1)}<span>%</span></p>
      <p className="metric-evidence">{evidence.replace(`${metric.value.toFixed(1)}% `, "")}</p>
      {metric.note ? <p className="metric-note">{metric.note}</p> : null}
    </article>
  );
}

export function EvidenceStamp({ children = "Illustrative example data" }: { children?: ReactNode }) {
  return <span className="sample-stamp"><Info aria-hidden="true" />{children}</span>;
}

export function EvidenceText({ value, n, ciLow, ciHigh }: { value: number; n: number; ciLow: number; ciHigh: number }) {
  const evidence = formatMetricEvidence({ label: "", value, n, ciLow, ciHigh });
  return <span className="evidence-text">{evidence ?? "Evidence unavailable"}</span>;
}