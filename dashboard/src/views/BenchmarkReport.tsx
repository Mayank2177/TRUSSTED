import React, { useEffect, useState } from 'react';
import { fetchBenchmarkReport } from '../api/client';
import { BenchmarkMetric } from '../api/types';
import { ShieldAlert, ShieldCheck } from 'lucide-react';

export const BenchmarkReport: React.FC = () => {
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBenchmarkReport()
      .then((data) => {
        setMetrics(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ color: 'var(--text-muted)' }}>Loading benchmark report...</div>;
  }

  return (
    <div>
      <div style={{
        backgroundColor: 'rgba(234, 179, 8, 0.1)',
        border: '1px solid rgba(234, 179, 8, 0.3)',
        borderRadius: '6px',
        padding: '12px 16px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        fontSize: '14px'
      }}>
        <ShieldAlert size={18} style={{ color: '#eab308' }} />
        <span>Prototype research scope. Fails on poisoned consistent facts (S6) and depends on reference feeds.</span>
      </div>

      <h2>Benchmark Report</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
        Honest evaluation of decision-integrity performance across attack and benign scenarios.
      </p>

      {/* Scenario Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '16px' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)', fontSize: '13px' }}>
            <th style={{ padding: '10px' }}>Scenario</th>
            <th style={{ padding: '10px' }}>Attack Type</th>
            <th style={{ padding: '10px' }}>Baseline ASR</th>
            <th style={{ padding: '10px' }}>Warrant ASR</th>
            <th style={{ padding: '10px' }}>Sample (n)</th>
            <th style={{ padding: '10px' }}>Result</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.scenario_id} style={{ borderBottom: '1px solid var(--border)', fontSize: '14px' }}>
              <td style={{ padding: '12px' }}><strong>{m.scenario_id}:</strong> {m.scenario_title}</td>
              <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{m.attack_type}</td>
              <td style={{ padding: '12px' }}>{(m.baseline_asr * 100).toFixed(1)}%</td>
              <td style={{ padding: '12px' }}>{(m.warrant_asr * 100).toFixed(1)}%</td>
              <td style={{ padding: '12px' }}>{m.n}</td>
              <td style={{ padding: '12px', fontWeight: 600, color: m.result_status === 'Mitigated' ? 'var(--allow)' : 'var(--block)' }}>
                {m.result_status}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};