export type DecisionResult = 'ALLOW' | 'STEP_UP' | 'BLOCK';

export interface BenchmarkMetric {
  scenario_id: string;
  scenario_title: string;
  attack_type: string;
  kind: 'attack' | 'benign';
  baseline_asr: number;
  warrant_asr: number;
  n: number;
  ci_lower: number;
  ci_upper: number;
  false_block_rate?: number;
  result_status: 'Mitigated' | 'Not mitigated' | 'Benign';
}

export interface RunDetail {
  id: string;
  scenario_id: string;
  status: 'completed' | 'error' | 'timeout';
  decision: DecisionResult;
  reasons: string[];
  latency_ms: number;
  llm_cost_micro_usd: number;
  created_at: string;
}

export interface ReceiptEvent {
  seq: number;
  type: string;
  payload: Record<string, unknown>;
  event_hash: string;
  prev_hash: string;
}

export interface Receipt {
  id: string;
  run_id: string;
  final_hash: string;
  signature: string;
  events: ReceiptEvent[];
}