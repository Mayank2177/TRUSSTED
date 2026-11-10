import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { verifyReceipt } from '../api/client';
import { Receipt } from '../api/types';

export const ReceiptViewer: React.FC = () => {
  const [pubKey, setPubKey] = useState('ed25519_pub_sample_key_9182374');
  const [verified, setVerified] = useState<boolean | null>(null);

  
  const receipt: Receipt = {
    id: 'rec_abc123',
    run_id: 'run_9f8b2c1a4e',
    final_hash: '7c4a8d09f21b65e3a1b2c3d4e5f67c4a8d09f21b65e3a1b2c3d4e5f67c4a8d09',
    signature: 'sig_sample_ed25519_hash_string...',
    events: [
      { seq: 0, type: 'intent', payload: { action: 'buy' }, event_hash: 'a1b2c3...', prev_hash: '000000...' },
      { seq: 1, type: 'observation', payload: { url: 'https://example.com' }, event_hash: 'd4e5f6...', prev_hash: 'a1b2c3...' },
      { seq: 2, type: 'facts', payload: { status: 'conflict' }, event_hash: '7c4a8d...', prev_hash: 'd4e5f6...' }
    ]
  };

  const handleVerify = async () => {
    const isValid = await verifyReceipt(receipt, pubKey);
    setVerified(isValid);
  };

  return (
    <div>
      <h2>Receipt & Evidence Chain</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
        Append-only hash-chained event record signed with Ed25519 for offline verification.
      </p>

      {/* Verify Panel */}
      <div style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '24px'
      }}>
        <h3>Offline Verification Panel</h3>
        <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
          <input
            type="text"
            value={pubKey}
            onChange={(e) => setPubKey(e.target.value)}
            placeholder="Enter public key..."
            style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid var(--border)', backgroundColor: 'var(--bg)', color: 'var(--text)' }}
          />
          <button
            onClick={handleVerify}
            style={{ padding: '8px 16px', backgroundColor: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
          >
            Verify Receipt
          </button>
        </div>

        {verified !== null && (
          <div style={{
            marginTop: '12px',
            padding: '10px',
            borderRadius: '4px',
            backgroundColor: verified ? 'rgba(27, 127, 75, 0.1)' : 'rgba(180, 35, 24, 0.1)',
            color: verified ? 'var(--allow)' : 'var(--block)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontWeight: 600
          }}>
            {verified ? <ShieldCheck size={18} /> : <ShieldAlert size={18} />}
            {verified ? 'Signature Valid & Hash Chain Intact' : 'Verification Failed'}
          </div>
        )}
      </div>

      {/* Hash Chain View */}
      <h3>Hash Chain Events</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
        {receipt.events.map((ev) => (
          <div key={ev.seq} style={{
            padding: '12px',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            display: 'flex',
            justifyContent: 'space-between'
          }}>
            <span>[{ev.seq}] TYPE: {ev.type.toUpperCase()}</span>
            <span style={{ color: 'var(--text-muted)' }}>HASH: {ev.event_hash}</span>
          </div>
        ))}
      </div>
    </div>
  );
};