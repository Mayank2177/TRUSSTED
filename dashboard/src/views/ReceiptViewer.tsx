import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { verifyReceipt } from '../api/client';
import { Receipt } from '../api/types';
import { Box, Typography, Card, CardContent, Button, TextField } from '@mui/material';

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
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>Receipt & Evidence Chain</Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
        Append-only hash-chained event record signed with Ed25519 for offline verification.
      </Typography>

      {/* Verify Panel */}
      <Card variant="outlined" sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 2 }}>Offline Verification Panel</Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              fullWidth
              size="small"
              value={pubKey}
              onChange={(e) => setPubKey(e.target.value)}
              placeholder="Enter public key..."
            />
            <Button variant="contained" onClick={handleVerify} sx={{ px: 3, py: 1, fontWeight: 600 }}>
              Verify Receipt
            </Button>
          </Box>

          {verified !== null && (
            <Box sx={{
              mt: 2,
              p: 1.5,
              borderRadius: 1,
              bgcolor: verified ? 'rgba(27, 127, 75, 0.1)' : 'rgba(180, 35, 24, 0.1)',
              color: verified ? 'success.main' : 'error.main',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              fontWeight: 600
            }}>
              {verified ? <ShieldCheck size={18} /> : <ShieldAlert size={18} />}
              {verified ? 'Signature Valid & Hash Chain Intact' : 'Verification Failed'}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Hash Chain View */}
      <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, mb: 2 }}>Hash Chain Events</Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {receipt.events.map((ev) => (
          <Card key={ev.seq} variant="outlined">
            <CardContent sx={{ py: '12px !important', display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '12px' }}>
              <Box component="span">[{ev.seq}] TYPE: {ev.type.toUpperCase()}</Box>
              <Box component="span" sx={{ color: 'text.secondary' }}>HASH: {ev.event_hash}</Box>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
};