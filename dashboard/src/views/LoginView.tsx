import React, { useState } from 'react';
import { Box, Button, Container, Card, CardContent, TextField, Typography, Alert } from '@mui/material';

interface LoginViewProps {
  onLoginSuccess: () => void;
  onSwitchToSignup: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess, onSwitchToSignup }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const formattedEmail = email.toLowerCase().trim();
    const storedUser = localStorage.getItem(`user_${formattedEmail}`);

    if (!storedUser) {
      setError('No account found with this email. Please sign up first.');
      return;
    }

    const userData = JSON.parse(storedUser);
    if (userData.password !== password) {
      setError('Incorrect password. Please try again.');
      return;
    }

    onLoginSuccess();
  };

  return (
    <Container maxWidth="xs" sx={{ height: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card variant="outlined" sx={{ width: '100%', p: 2, bgcolor: 'rgba(15, 23, 42, 0.85)', borderColor: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h5" component="h2" align="center" gutterBottom sx={{ fontWeight: 'bold' }}>
            TRUSSTED Sign In
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Access your risk verification suite
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email Address"
              type="email"
              variant="outlined"
              fullWidth
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextField
              label="Password"
              type="password"
              variant="outlined"
              fullWidth
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button type="submit" variant="contained" size="large" fullWidth sx={{ mt: 1, bgcolor: '#6366F1', '&:hover': { bgcolor: '#4F46E5' } }}>
              Sign In
            </Button>
            <Button variant="text" size="small" onClick={onSwitchToSignup} sx={{ color: '#818CF8', textTransform: 'none' }}>
              Don't have an account? Sign Up
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
};