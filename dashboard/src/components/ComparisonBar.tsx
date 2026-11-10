import React from 'react';

interface ComparisonBarProps {
  label: string;
  baseline: number;
  warrant: number;
}

export const ComparisonBar: React.FC<ComparisonBarProps> = ({ label, baseline, warrant }) => {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
        <span>{label}</span>
        <span style={{ color: 'var(--text-muted)' }}>Baseline: {(baseline * 100)}% | Warrant: {(warrant * 100)}%</span>
      </div>
      <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', backgroundColor: 'var(--border)' }}>
        <div style={{ width: `${baseline * 100}%`, backgroundColor: 'var(--block)', opacity: 0.7 }} title="Baseline ASR" />
        <div style={{ width: `${warrant * 100}%`, backgroundColor: 'var(--allow)' }} title="Warrant ASR" />
      </div>
    </div>
  );
};