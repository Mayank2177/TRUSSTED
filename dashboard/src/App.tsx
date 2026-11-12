import React, { useState } from 'react';
import { Routes, Route, Link, useLocation, useNavigate, Navigate } from 'react-router-dom';
import {
  ThemeProvider,
  CssBaseline,
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  useMediaQuery,
  useTheme,
  Button,
} from '@mui/material';
import {
  MessageSquare,
  CheckSquare,
  FileText,
  BarChart3,
  Sparkles,
  Sun,
  Moon,
  Menu,
} from 'lucide-react';
import { darkTheme, lightTheme } from './theme';
import { ChatView } from './views/ChatView';
import { RunDetail } from './views/RunDetail';
import { ReceiptViewer } from './views/ReceiptViewer';
import { BenchmarkReport } from './views/BenchmarkReport';
import { LandingView } from './views/LandingView';
import { LoginView } from './views/LoginView';
import { SignupView } from './views/SignupView';

interface DashboardLayoutProps {
  mode: 'dark' | 'light';
  toggleTheme: () => void;
  isAuthenticated: boolean;
  setIsAuthenticated: (val: boolean) => void;
}

const DRAWER_WIDTH = 260;

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ mode, toggleTheme, isAuthenticated, setIsAuthenticated }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const isLandingPage = location.pathname === '/';
  const isAuthPage = location.pathname === '/login' || location.pathname === '/signup';

  const handleDrawerToggle = () => {
    setMobileOpen((prev) => !prev);
  };

  const navItems = [
    { path: '/chat', label: 'Shop with AI', icon: MessageSquare },
    { path: '/runs', label: 'Runs', icon: CheckSquare },
    { path: '/receipts', label: 'Receipts', icon: FileText },
    { path: '/benchmark', label: 'Benchmarks', icon: BarChart3 },
  ];

  const drawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 2.5 }}>
      <Box
        component={Link}
        to="/"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          mb: 4,
          px: 1,
          textDecoration: 'none',
          color: 'text.primary',
        }}
      >
        <Box
          sx={{
            width: 34,
            height: 34,
            flexShrink: 0,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #6C94FF 0%, #4F46E5 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Sparkles size={18} color="#FFF" aria-hidden="true" />
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 900, letterSpacing: '-0.03em', fontSize: '18px' }}>
          TRUSSTED
        </Typography>
      </Box>

      <List aria-label="Authenticated app navigation" sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.path}
              component={Link}
              to={item.path}
              selected={isActive}
              onClick={() => {
                if (isMobile) setMobileOpen(false);
              }}
              sx={{
                borderRadius: 2,
                py: 1.25,
                px: 1.75,
                bgcolor: isActive ? 'rgba(108, 148, 255, 0.14)' : 'transparent',
                border: '1px solid',
                borderColor: isActive ? 'rgba(108, 148, 255, 0.35)' : 'transparent',
                color: isActive ? 'primary.main' : 'text.secondary',
                '&:hover': {
                  bgcolor: 'action.hover',
                  color: 'text.primary',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
                <Icon size={18} aria-hidden="true" />
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                sx={{
                  '& .MuiListItemText-primary': {
                    fontSize: '14px',
                    fontWeight: isActive ? 700 : 500,
                  },
                }}
              />
            </ListItemButton>
          );
        })}
      </List>

      <Box sx={{ mt: 'auto', pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button
          fullWidth
          variant="outlined"
          color="error"
          size="small"
          onClick={() => {
            setIsAuthenticated(false);
            navigate('/');
          }}
          sx={{ fontWeight: 700, borderRadius: 2 }}
        >
          Sign Out
        </Button>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'background.default', width: '100%' }}>
      {/* Header */}
      <Box
        component="header"
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 1200,
          px: { xs: 2.5, md: 4 },
          py: 2,
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          ml: { md: isLandingPage || isAuthPage ? 0 : `${DRAWER_WIDTH}px` },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {!isLandingPage && !isAuthPage && isMobile && (
            <IconButton color="inherit" aria-label="Open drawer" edge="start" onClick={handleDrawerToggle}>
              <Menu size={20} />
            </IconButton>
          )}

          <Typography
            variant="h6"
            onClick={() => navigate(isAuthenticated ? '/chat' : '/')}
            sx={{
              fontWeight: 900,
              letterSpacing: '-0.03em',
              cursor: 'pointer',
              background: 'linear-gradient(135deg, #6C94FF 0%, #4CC38A 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            TRUSSTED
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {isLandingPage && (
            <>
              <Button variant="outlined" size="small" onClick={() => navigate('/login')} sx={{ borderColor: 'rgba(108,148,255,0.4)', color: 'text.primary', fontWeight: 700 }}>
                Sign In
              </Button>
              <Button variant="contained" size="small" onClick={() => navigate('/signup')} sx={{ bgcolor: '#6C94FF', fontWeight: 700 }}>
                Sign Up
              </Button>
            </>
          )}

          <IconButton onClick={toggleTheme} size="small" sx={{ border: '1px solid', borderColor: 'divider', color: 'text.primary' }}>
            {mode === 'dark' ? <Sun size={17} color="#E3B341" /> : <Moon size={17} color="#6C94FF" />}
          </IconButton>
        </Box>
      </Box>

      {/* Body */}
      <Box sx={{ display: 'flex', flexGrow: 1 }}>
        {!isLandingPage && !isAuthPage && (
          <Box component="nav" aria-label="Sidebar" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
            {isMobile ? (
              <Drawer
                variant="temporary"
                open={mobileOpen}
                onClose={handleDrawerToggle}
                ModalProps={{ keepMounted: true }}
                sx={{
                  display: { xs: 'block', md: 'none' },
                  '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box', bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider' },
                }}
              >
                {drawerContent}
              </Drawer>
            ) : (
              <Drawer
                variant="permanent"
                open
                sx={{
                  display: { xs: 'none', md: 'block' },
                  '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box', bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider' },
                }}
              >
                {drawerContent}
              </Drawer>
            )}
          </Box>
        )}

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: { xs: 2.5, md: isLandingPage || isAuthPage ? 0 : 4 },
            width: { md: isLandingPage || isAuthPage ? '100%' : `calc(100% - ${DRAWER_WIDTH}px)` },
            maxWidth: isLandingPage || isAuthPage ? 'none' : '1320px',
            mx: 'auto',
          }}
        >
          <Routes>
            {/* Stage 1: Public Website */}
            <Route path="/" element={<LandingView onNavigateToLogin={() => navigate('/login')} onNavigateToSignup={() => navigate('/signup')} onNavigateToDashboard={() => navigate('/chat')} />} />

            {/* Stage 2: Authentication */}
            <Route path="/login" element={<LoginView onLoginSuccess={() => { setIsAuthenticated(true); navigate('/chat'); }} onSwitchToSignup={() => navigate('/signup')} />} />
            <Route path="/signup" element={<SignupView onSignupSuccess={() => { setIsAuthenticated(true); navigate('/chat'); }} onSwitchToLogin={() => navigate('/login')} />} />

            {/* Stage 3: Main TRUSSTED Application */}
            <Route path="/dashboard" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={isAuthenticated ? <ChatView /> : <Navigate to="/login" replace />} />
            <Route path="/runs" element={isAuthenticated ? <RunDetail /> : <Navigate to="/login" replace />} />
            <Route path="/runs/:runId" element={isAuthenticated ? <RunDetail /> : <Navigate to="/runs" replace />} />
            <Route path="/receipts" element={isAuthenticated ? <ReceiptViewer /> : <Navigate to="/login" replace />} />
            <Route path="/receipts/:receiptId" element={isAuthenticated ? <ReceiptViewer /> : <Navigate to="/receipts" replace />} />
            <Route path="/benchmark" element={isAuthenticated ? <BenchmarkReport /> : <Navigate to="/login" replace />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </Box>
    </Box>
  );
};

export function App() {
  const [mode, setMode] = useState<'dark' | 'light'>('dark');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const toggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeProvider theme={mode === 'dark' ? darkTheme : lightTheme}>
      <CssBaseline />
      <DashboardLayout mode={mode} toggleTheme={toggleTheme} isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated} />
    </ThemeProvider>
  );
}

export default App;