import React from 'react';

interface EventItem {
  seq: number;
  type: string;
  event_hash: string;
}

interface HashChainViewProps {
  events: EventItem[];
}

export const HashChainView: React.FC<HashChainViewProps> = ({ events }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {events.map((ev) => (
        <div key={ev.seq} style={{
          padding: '12px',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          backgroundColor: 'var(--surface)'
        }}>
          <span>[{ev.seq}] TYPE: {ev.type.toUpperCase()}</span>
          <span style={{ color: 'var(--text-muted)' }}>HASH: {ev.event_hash}</span>
        </div>
      ))}
    </div>
  );
};