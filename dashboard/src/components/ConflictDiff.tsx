import React from 'react';

interface ConflictDiffProps {
  sourceText: string;
  observedText: string;
}

export const ConflictDiff: React.FC<ConflictDiffProps> = ({ sourceText, observedText }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
      <div style={{ padding: '12px', backgroundColor: 'rgba(180, 35, 24, 0.05)', border: '1px solid var(--block)', borderRadius: '6px' }}>
        <div style={{ color: 'var(--block)', fontWeight: 600, marginBottom: '6px' }}>Reference Source</div>
        <div>{sourceText}</div>
      </div>
      <div style={{ padding: '12px', backgroundColor: 'rgba(234, 179, 8, 0.05)', border: '1px solid #eab308', borderRadius: '6px' }}>
        <div style={{ color: '#eab308', fontWeight: 600, marginBottom: '6px' }}>Observed Page</div>
        <div>{observedText}</div>
      </div>
    </div>
  );
};