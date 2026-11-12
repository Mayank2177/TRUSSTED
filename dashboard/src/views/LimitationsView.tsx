import React from 'react';
import { Box, Typography, Card, CardContent } from '@mui/material';
import { ShieldAlert } from 'lucide-react';

export const LimitationsView: React.FC = () => {
  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>System Limitations & Constraints</Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
        Transparent documentation of known platform boundaries and edge cases.
      </Typography>

      <Card variant="outlined" sx={{ borderColor: 'warning.main' }}>
        <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
          <ShieldAlert color="var(--mui-palette-warning-main)" size={24} />
          <Box>
            <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600, mb: 1 }}>
              Known S6 Limitation: Poisoned-but-Consistent Facts
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
              The current verification pipeline relies on consistency checks across extracted assertions and independent evidence streams. If an attacker introduces poisoned data that remains internally consistent across all cross-checked sources, the pipeline may permit the option. Future iterations will incorporate deeper anomaly detection to mitigate this limitation.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};