import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

export const LimitationsBanner: React.FC = () => (
  <div style={{
    backgroundColor: 'var(--surface)',
    borderLeft: '4px solid var(--step-up)',
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '13px',
    marginBottom: '20px'
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <ShieldAlert size={18} color="var(--step-up)" />
      <span>Prototype research scope. Fails on poisoned consistent facts (S6) and depends on reference feeds.</span>
    </div>
    <Link to="/limitations" style={{ color: 'var(--accent)', fontWeight: 500, textDecoration: 'none' }}>
      View all limitations &rarr;
    </Link>
  </div>
);