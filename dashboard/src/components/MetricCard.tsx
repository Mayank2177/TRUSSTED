import React from 'react';

interface Props {
  title: string;
  value: string | number;
  n: number;
  ci?: [number, number];
}

export const MetricCard: React.FC<Props> = ({ title, value, n, ci }) => {
  if (n === undefined || n === null) {
    throw new Error('MetricCard violation: Component refuses to render without sample size (n).');
  }

  return (
    <div style={{
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '16px',
      minWidth: '220px'
    }}>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>{title}</div>
      <div style={{ fontSize: '24px', fontWeight: 600, color: 'var(--text)' }}>{value}</div>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
        n = {n} {ci ? `| 95% CI [${ci[0]}, ${ci[1]}]` : ''}
      </div>
    </div>
  );
};