import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2 } from 'lucide-react';

interface Stage {
  name: string;
  status: 'passed' | 'failed' | 'skipped';
  details: string;
}

export const DecisionTimeline: React.FC = () => {
  const [expandedStage, setExpandedStage] = useState<number | null>(0);

  const stages: Stage[] = [
    { name: '1. Extract', status: 'passed', details: 'Extracted typed ProductFact list via schema-constrained LLM[cite: 8].' },
    { name: '2. Cross-check', status: 'failed', details: 'Emitted FactConflict record: high severity price/spec mismatch[cite: 8, 13].' },
    { name: '3. Rank', status: 'passed', details: 'Deterministic scorer evaluated candidates against UserIntent constraints[cite: 8, 13].' },
    { name: '4. Perturb', status: 'passed', details: 'Ran strip_persuasion and shuffle_order stability checks[cite: 8, 13].' },
    { name: '5. Decide', status: 'passed', details: 'Policy engine returned BLOCK due to high-severity conflict[cite: 8, 13].' },
    { name: '6. Credential', status: 'skipped', details: 'Skipped because decision was BLOCK (no payment credential issued)[cite: 8, 14].' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
      <strong>Decision Pipeline Timeline</strong>
      {stages.map((stage, idx) => {
        const isExpanded = expandedStage === idx;
        return (
          <div key={idx} style={{
            border: '1px solid var(--border)',
            borderRadius: '6px',
            backgroundColor: 'var(--surface)',
            overflow: 'hidden'
          }}>
            <div
              onClick={() => setExpandedStage(isExpanded ? null : idx)}
              style={{
                padding: '10px 14px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 500
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} color={stage.status === 'failed' ? 'var(--block)' : 'var(--allow)'} />
                <span>{stage.name}</span>
              </div>
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {isExpanded && (
              <div style={{
                padding: '12px 14px',
                borderTop: '1px solid var(--border)',
                fontSize: '12px',
                color: 'var(--text-muted)',
                backgroundColor: 'var(--bg)'
              }}>
                {stage.details}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};