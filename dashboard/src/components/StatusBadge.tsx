import React from 'react';
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { DecisionResult } from '../api/types';

interface Props {
  status: DecisionResult;
}

export const StatusBadge: React.FC<Props> = ({ status }) => {
  const styles = {
    ALLOW: { bg: 'var(--allow)', icon: <CheckCircle size={14} />, label: 'ALLOW' },
    STEP_UP: { bg: 'var(--step-up)', icon: <AlertTriangle size={14} />, label: 'STEP UP' },
    BLOCK: { bg: 'var(--block)', icon: <XCircle size={14} />, label: 'BLOCK' }
  };

  const config = styles[status] || styles.BLOCK;

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 10px',
      borderRadius: '999px',
      backgroundColor: config.bg,
      color: '#FFFFFF',
      fontSize: '12px',
      fontWeight: 600
    }}>
      {config.icon}
      {config.label}
    </span>
  );
};