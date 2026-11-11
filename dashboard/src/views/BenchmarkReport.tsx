import React, { useEffect, useState } from 'react';
import { fetchBenchmarkReport } from '../api/client';
import { BenchmarkMetric } from '../api/types';
import { ShieldAlert } from 'lucide-react';
import { Box, Typography, Card, CardContent } from '@mui/material';

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
    return <Box sx={{ color: 'text.secondary' }}>Loading benchmark report...</Box>;
  }

  return (
    <Box>
      <Box sx={{
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
      </Box>

      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Benchmark Report</Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
        Honest evaluation of decision-integrity performance across attack and benign scenarios.
      </Typography>

      {/* Scenario Table / Illustrative View */}
      {metrics.length === 0 ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>Illustrative Evaluation State</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              No verified production benchmark dataset is currently loaded. Placeholder states are shown to prevent unverified performance claims.
            </Typography>
          </CardContent>
        </Card>
      ) : (
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
      )}
    </Box>
  );
};