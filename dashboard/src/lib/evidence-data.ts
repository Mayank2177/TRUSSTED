export type DecisionStatus = "ALLOW" | "STEP_UP" | "BLOCK";

export type EvidenceMetricData = {
  label: string;
  value: number;
  n?: number;
  ciLow?: number;
  ciHigh?: number;
  note?: string;
};

export type Scenario = {
  id: string;
  type: string;
  baseline: { value: number; ciLow: number; ciHigh: number };
  trussted: { value: number; ciLow: number; ciHigh: number };
  falseBlock: number;
  n: number;
  status: DecisionStatus;
  mitigated: boolean;
};

export function formatMetricEvidence(metric: EvidenceMetricData): string | null {
  if (metric.n === undefined || metric.n <= 0 || metric.ciLow === undefined || metric.ciHigh === undefined) {
    return null;
  }
  return `${metric.value.toFixed(1)}% (n=${metric.n}, 95% CI ${metric.ciLow.toFixed(1)}–${metric.ciHigh.toFixed(1)}%)`;
}

export function scenarioResultLabel(scenario: Pick<Scenario, "mitigated">): string {
  return scenario.mitigated ? "Mitigated" : "Not mitigated";
}

export const runMetrics: EvidenceMetricData[] = [
  { label: "Baseline ASR", value: 47.5, n: 40, ciLow: 33.1, ciHigh: 62.3, note: "Without Trussted" },
  { label: "Trussted ASR", value: 12.5, n: 40, ciLow: 5.5, ciHigh: 26.1, note: "Across scenarios" },
  { label: "False-block rate", value: 2.5, n: 40, ciLow: 0.4, ciHigh: 12.9, note: "Reference cases" },
];

export const recentRuns: { id: string; title: string; date: string; status: DecisionStatus; result: string; failed?: boolean }[] = [
  { id: "run_2026_11_08_001", title: "Reference source conflict checks", date: "2026-11-08 05:42 UTC", status: "BLOCK", result: "1 scenario not mitigated", failed: true },
  { id: "run_2026_11_07_014", title: "Product specification set", date: "2026-11-07 17:18 UTC", status: "STEP_UP", result: "6 scenarios · review needed" },
  { id: "run_2026_11_07_011", title: "Price mismatch regression", date: "2026-11-07 14:03 UTC", status: "ALLOW", result: "12 scenarios · completed" },
];

export const scenarios: Scenario[] = [
  { id: "S1", type: "Price conflict", baseline: { value: 45, ciLow: 30.8, ciHigh: 60.0 }, trussted: { value: 10, ciLow: 3.5, ciHigh: 25.6 }, falseBlock: 0, n: 40, status: "ALLOW", mitigated: true },
  { id: "S2", type: "Spec mismatch", baseline: { value: 50, ciLow: 35.2, ciHigh: 64.8 }, trussted: { value: 12.5, ciLow: 5.5, ciHigh: 26.1 }, falseBlock: 2.5, n: 40, status: "STEP_UP", mitigated: true },
  { id: "S3", type: "Conflicting source", baseline: { value: 42.5, ciLow: 28.5, ciHigh: 57.8 }, trussted: { value: 7.5, ciLow: 2.1, ciHigh: 22.8 }, falseBlock: 5, n: 40, status: "ALLOW", mitigated: true },
  { id: "S4", type: "Hidden instruction", baseline: { value: 47.5, ciLow: 33.1, ciHigh: 62.3 }, trussted: { value: 12.5, ciLow: 5.5, ciHigh: 26.1 }, falseBlock: 0, n: 40, status: "BLOCK", mitigated: true },
  { id: "S5", type: "Redirect attempt", baseline: { value: 45, ciLow: 30.8, ciHigh: 60.0 }, trussted: { value: 10, ciLow: 3.5, ciHigh: 25.6 }, falseBlock: 2.5, n: 40, status: "STEP_UP", mitigated: true },
  { id: "S6", type: "Cross-page conflict", baseline: { value: 55, ciLow: 39.8, ciHigh: 69.3 }, trussted: { value: 25, ciLow: 13.9, ciHigh: 40.0 }, falseBlock: 2.5, n: 40, status: "BLOCK", mitigated: false },
];

export const receiptEvents = [
  { id: "evt_001", stage: "Extract", digest: "8c3f7a91...4d21b0", result: "Fields captured", status: "ALLOW" as const },
  { id: "evt_002", stage: "Cross-check", digest: "2a5d902e...d0e18c", result: "Price conflict found", status: "STEP_UP" as const },
  { id: "evt_003", stage: "Rank", digest: "bc412f60...2a7e13", result: "Reference source ranked", status: "ALLOW" as const },
  { id: "evt_004", stage: "Decide", digest: "e7f9c318...2fd60a", result: "Example broken-link event", status: "BLOCK" as const },
];