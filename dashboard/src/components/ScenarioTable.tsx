import React from 'react';
import { BenchmarkMetric } from '../api/types';

interface Props {
  metrics: BenchmarkMetric[];
}

export const ScenarioTable: React.FC<Props> = ({ metrics }) => (
  <div style={{ overflowX: 'auto' }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
          <th style={{ padding: '10px' }} scope="col">Scenario</th>
          <th style={{ padding: '10px' }} scope="col">Attack Type</th>
          <th style={{ padding: '10px' }} scope="col">Baseline ASR</th>
          <th style={{ padding: '10px' }} scope="col">Warrant ASR</th>
          <th style={{ padding: '10px' }} scope="col">Sample (n)</th>
          <th style={{ padding: '10px' }} scope="col">Result</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((m) => (
          <tr key={m.scenario_id} style={{ borderBottom: '1px solid var(--border)' }}>
            <td style={{ padding: '10px', fontWeight: 500 }}>{m.scenario_id}: {m.scenario_title}</td>
            <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{m.attack_type}</td>
            <td style={{ padding: '10px' }}>{(m.baseline_asr * 100).toFixed(1)}%</td>
            <td style={{ padding: '10px' }}>{(m.warrant_asr * 100).toFixed(1)}%</td>
            <td style={{ padding: '10px' }}>{m.n}</td>
            <td style={{ padding: '10px' }}>
              <span style={{
                color: m.result_status === 'Mitigated' ? 'var(--allow)' : 'var(--block)',
                fontWeight: 600
              }}>
                {m.result_status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);