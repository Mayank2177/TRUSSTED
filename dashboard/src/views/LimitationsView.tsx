import React from 'react';

export const LimitationsView: React.FC = () => (
  <div>
    <h2>Known Limitations</h2>
    <ol style={{ lineHeight: '1.6', color: 'var(--text-muted)' }}>
      <li><strong>Poisoned-but-consistent facts:</strong> Both sources agreeing on a falsehood pass checks (Scenario S6).</li>
      <li><strong>LLM extraction risk:</strong> Schema constraints reduce, but do not eliminate, untrusted text risks.</li>
      <li><strong>Perturbation latency/cost:</strong> Checks add overhead and can trigger false positives on close choices.</li>
      <li><strong>User Intent dependency:</strong> Deterministic ranking requires explicit intent, which many users lack.</li>
      <li><strong>Receipt scope:</strong> A signed receipt proves record integrity, not absolute input truth.</li>
      <li><strong>Synthetic fixtures:</strong> Results derive from synthetic fixtures and do not generalise directly to the open web without testing.</li>
    </ol>
  </div>
);