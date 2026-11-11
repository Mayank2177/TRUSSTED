import React, { useState } from 'react';
import { Box, Button, Container, Card, CardContent, TextField, Typography, Alert } from '@mui/material';

interface SignupViewProps {
  onSignupSuccess: () => void;
  onSwitchToLogin: () => void;
}

export const SignupView: React.FC<SignupViewProps> = ({ onSignupSuccess, onSwitchToLogin }) => {
  const [fullName, setFullName] = useState('');
  const [organization, setOrganization] = useState('');
  const [role, setRole] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    // Check if user already exists
    const existingUser = localStorage.getItem(`user_${email.toLowerCase().trim()}`);
    if (existingUser) {
      setError('An account with this email already exists. Please sign in instead.');
      return;
    }

    // Save registered user details in local storage
    const userData = {
      fullName,
      organization,
      role,
      email: email.toLowerCase().trim(),
      password,
    };

    localStorage.setItem(`user_${email.toLowerCase().trim()}`, JSON.stringify(userData));
    onSignupSuccess();
  };

  return (
    <Container maxWidth="xs" sx={{ height: '85vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card variant="outlined" sx={{ width: '100%', p: 2, bgcolor: 'rgba(15, 23, 42, 0.85)', borderColor: 'rgba(255,255,255,0.08)', borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h5" component="h2" align="center" gutterBottom sx={{ fontWeight: 'bold' }}>
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Register for TRUSSTED Gateway Access
          </Typography>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Full Name"
              type="text"
              variant="outlined"
              fullWidth
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />


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
            <TextField
              label="Confirm Password"
              type="password"
              variant="outlined"
              fullWidth
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            <Button type="submit" variant="contained" size="large" fullWidth sx={{ mt: 1, bgcolor: '#6366F1', '&:hover': { bgcolor: '#4F46E5' } }}>
              Register & Sign In
            </Button>
            <Button variant="text" size="small" onClick={onSwitchToLogin} sx={{ color: '#818CF8', textTransform: 'none' }}>
              Already have an account? Sign In
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
};