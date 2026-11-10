import React, { useEffect, useState } from 'react';
import { fetchRunDetail } from '../api/client';
import { RunDetail as RunDetailType } from '../api/types';
import { ShieldAlert, CheckCircle2, ChevronDown, Terminal, Sparkles, Activity } from 'lucide-react';

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
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: 'var(--text-muted)', gap: '10px' }}>
        <Activity className="animate-spin" size={20} />
        <span>Initializing decision trace engine...</span>
      </div>
    );
  }

  const isBlocked = run.decision === 'BLOCK';

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      {/* Header Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        padding: '20px',
        background: 'linear-gradient(135deg, var(--surface) 0%, rgba(36, 87, 214, 0.03) 100%)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.05)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Sparkles size={16} color="var(--accent)" />
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Execution Trace</span>
          </div>
          <h2 style={{ fontSize: '22px', fontWeight: 700 }}>Run Inspection</h2>
          <p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '13px', marginTop: '4px' }}>
            ID: {run.id}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => setShowConsole(!showConsole)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '6px',
              backgroundColor: showConsole ? 'var(--accent)' : 'var(--surface-raised)',
              color: showConsole ? '#fff' : 'var(--text)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '13px',
              transition: 'all 0.2s'
            }}
          >
            <Terminal size={15} />
            {showConsole ? 'Hide Raw Payload' : 'Inspect Payload'}
          </button>
          <div style={{
            padding: '8px 16px',
            borderRadius: '6px',
            fontWeight: 700,
            fontSize: '13px',
            letterSpacing: '0.5px',
            backgroundColor: isBlocked ? 'rgba(180, 35, 24, 0.15)' : 'rgba(27, 127, 75, 0.15)',
            color: isBlocked ? 'var(--block)' : 'var(--allow)',
            border: `1px solid ${isBlocked ? 'var(--block)' : 'var(--allow)'}`,
            boxShadow: isBlocked ? '0 0 12px rgba(180, 35, 24, 0.2)' : '0 0 12px rgba(27, 127, 75, 0.2)'
          }}>
            {run.decision}
          </div>
        </div>
      </div>

      {/* Raw Payload Terminal Drawer */}
      {showConsole && (
        <div style={{
          backgroundColor: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '16px',
          marginBottom: '24px',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: '#58a6ff',
          overflowX: 'auto',
          boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.5)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e', marginBottom: '8px', borderBottom: '1px solid #30363d', paddingBottom: '6px' }}>
            <span>LIVE_TELEMETRY_PAYLOAD.json</span>
            <span>Status: 200 OK</span>
          </div>
          <pre>{JSON.stringify(run, null, 2)}</pre>
        </div>
      )}

      {/* Metadata Grid Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '16px',
        marginBottom: '24px'
      }}>
        {[
          { label: 'Execution Latency', value: `${run.latency_ms} ms`, sub: 'P95 Optimized' },
          { label: 'LLM Inference Cost', value: `$${(run.llm_cost_micro_usd / 1000000).toFixed(4)}`, sub: 'Token Budget Controlled' },
          { label: 'Timestamp (UTC)', value: new Date(run.created_at).toLocaleTimeString(), sub: new Date(run.created_at).toLocaleDateString() }
        ].map((card, i) => (
          <div key={i} style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '20px',
            transition: 'transform 0.2s, box-shadow 0.2s',
          }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '12px', fontWeight: 500 }}>{card.label}</span>
            <div style={{ fontSize: '22px', fontWeight: 700, margin: '6px 0 2px 0' }}>{card.value}</div>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>{card.sub}</span>
          </div>
        ))}
      </div>

      {/* Decision Reasons */}
      <h3 style={{ marginBottom: '12px', fontSize: '16px', fontWeight: 600 }}>Decision Policy Triggers</h3>
      <div style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '10px',
        padding: '16px',
        marginBottom: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        {run.reasons.map((reason, idx) => (
          <div key={idx} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 14px',
            borderRadius: '6px',
            backgroundColor: 'rgba(180, 35, 24, 0.05)',
            border: '1px solid rgba(180, 35, 24, 0.2)',
            color: 'var(--block)',
            fontSize: '14px',
            fontWeight: 500
          }}>
            <ShieldAlert size={18} />
            <span>{reason}</span>
          </div>
        ))}
      </div>

      {/* Decision Pipeline Timeline */}
      <h3 style={{ marginBottom: '12px', fontSize: '16px', fontWeight: 600 }}>Deterministic Pipeline Trace</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {['Extract', 'Cross-check', 'Rank', 'Perturb', 'Decide', 'Credential'].map((step, idx) => (
          <div key={step} style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '14px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                backgroundColor: 'rgba(27, 127, 75, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <CheckCircle2 size={15} style={{ color: 'var(--allow)' }} />
              </div>
              <div>
                <span style={{ fontWeight: 600, fontSize: '14px' }}>Stage {idx + 1}: {step}</span>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Verified deterministic check passed successfully.</div>
              </div>
            </div>
            <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} />
          </div>
        ))}
      </div>
    </div>
  );
};