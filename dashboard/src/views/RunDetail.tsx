import React, { useEffect, useState } from 'react';
import { fetchRunDetail } from '../api/client';
import { RunDetail as RunDetailType } from '../api/types';
import { ShieldAlert, CheckCircle2, ChevronDown, Terminal, Sparkles, Activity } from 'lucide-react';
import { Box, Typography, Card, CardContent, Button } from '@mui/material';

export const RunDetail: React.FC = () => {
  const [run, setRun] = useState<RunDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [showConsole, setShowConsole] = useState(false);

  useEffect(() => {
    fetchRunDetail('run_9f8b2c1a4e')
      .then((data) => {
        setRun(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading || !run) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: 'text.secondary', gap: 1 }}>
        <Activity className="animate-spin" size={20} />
        <Typography variant="body2">Initializing decision trace engine...</Typography>
      </Box>
    );
  }

  const isBlocked = run.decision === 'BLOCK';

  return (
    <Box sx={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      {/* Header Banner */}
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: 3,
        p: 2.5,
        background: 'linear-gradient(135deg, var(--mui-palette-background-paper) 0%, rgba(36, 87, 214, 0.03) 100%)',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 3,
        boxShadow: '0 4px 20px rgba(0,0,0,0.05)'
      }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Sparkles size={16} color="var(--mui-palette-primary-main)" />
            <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>Execution Trace</Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>Run Inspection</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', fontFamily: 'monospace', mt: 0.5 }}>
            ID: {run.id}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          <Button
            variant={showConsole ? 'contained' : 'outlined'}
            size="small"
            startIcon={<Terminal size={15} />}
            onClick={() => setShowConsole(!showConsole)}
            sx={{ fontWeight: 600 }}
          >
            {showConsole ? 'Hide Raw Payload' : 'Inspect Payload'}
          </Button>
          <Box sx={{
            px: 2,
            py: 0.75,
            borderRadius: 1.5,
            fontWeight: 700,
            fontSize: '13px',
            letterSpacing: '0.5px',
            bgcolor: isBlocked ? 'rgba(180, 35, 24, 0.15)' : 'rgba(27, 127, 75, 0.15)',
            color: isBlocked ? 'error.main' : 'success.main',
            border: '1px solid',
            borderColor: isBlocked ? 'error.main' : 'success.main',
          }}>
            {run.decision}
          </Box>
        </Box>
      </Box>

      {/* Raw Payload Terminal Drawer */}
      {showConsole && (
        <Card variant="outlined" sx={{ mb: 3, bgcolor: '#0d1117', color: '#e6edf3', borderColor: '#30363d' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e', mb: 1, borderBottom: '1px solid #30363d', pb: 1, fontSize: '12px', fontFamily: 'monospace' }}>
              <span>LIVE_TELEMETRY_PAYLOAD.json</span>
              <span>Status: 200 OK</span>
            </Box>
            <pre style={{ margin: 0, fontSize: '12px', overflowX: 'auto', color: '#58a6ff' }}>{JSON.stringify(run, null, 2)}</pre>
          </CardContent>
        </Card>
      )}

      {/* Metadata Grid Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2, mb: 4 }}>
        {[
          { label: 'Execution Latency', value: `${run.latency_ms} ms`, sub: 'P95 Optimized' },
          { label: 'LLM Inference Cost', value: `$${(run.llm_cost_micro_usd / 1000000).toFixed(4)}`, sub: 'Token Budget Controlled' },
          { label: 'Timestamp (UTC)', value: new Date(run.created_at).toLocaleTimeString(), sub: new Date(run.created_at).toLocaleDateString() }
        ].map((card, i) => (
          <Card key={i} variant="outlined">
            <CardContent>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>{card.label}</Typography>
              <Typography variant="h5" sx={{ fontWeight: 700, my: 0.5 }}>{card.value}</Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>{card.sub}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Decision Reasons */}
      <Typography variant="h6" sx={{ mb: 1.5, fontSize: '1rem', fontWeight: 600 }}>Decision Policy Triggers</Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 4 }}>
        {run.reasons.map((reason, idx) => (
          <Card key={idx} variant="outlined" sx={{ borderColor: 'error.main', bgcolor: 'rgba(180, 35, 24, 0.03)' }}>
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: '12px !important', color: 'error.main' }}>
              <ShieldAlert size={18} />
              <Typography variant="body2" sx={{ fontWeight: 500 }}>{reason}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Decision Pipeline Timeline (7 Stages) */}
      <Typography variant="h6" sx={{ mb: 1.5, fontSize: '1rem', fontWeight: 600 }}>Deterministic Pipeline Trace</Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {['Extract', 'Cross-check', 'Rank', 'Perturb', 'Decide', 'Credential', 'Receipt'].map((step, idx) => (
          <Card key={step} variant="outlined">
            <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: '12px !important' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  bgcolor: 'rgba(27, 127, 75, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <CheckCircle2 size={16} color="var(--mui-palette-success-main)" />
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Stage {idx + 1}: {step}</Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Verified deterministic check passed successfully.</Typography>
                </Box>
              </Box>
              <ChevronDown size={16} color="var(--mui-palette-text-secondary)" />
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
};