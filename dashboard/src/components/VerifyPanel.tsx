import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';

interface VerifyPanelProps {
  onVerify: (pubKey: string) => Promise<boolean>;
}

export const VerifyPanel: React.FC<VerifyPanelProps> = ({ onVerify }) => {
  const [pubKey, setPubKey] = useState('ed25519_pub_sample_key_9182374');
  const [verified, setVerified] = useState<boolean | null>(null);

  const handleCheck = async () => {
    const isValid = await onVerify(pubKey);
    setVerified(isValid);
  };

  return (
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
          onClick={handleCheck}
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
  );
};