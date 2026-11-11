import { createTheme, alpha } from '@mui/material/styles';

// Warrant Design Tokens
export const warrantColors = {
  light: {
    background: '#FFFFFF',
    surface: '#F6F7F9',
    raisedSurface: '#FFFFFF',
    border: '#D9DDE3',
    text: '#14171C',
    mutedText: '#555E6B',
    accent: '#2457D6',
  },
  dark: {
    background: '#0F1115',
    surface: '#171A21',
    raisedSurface: '#1E222B',
    border: '#2C323D',
    text: '#E8EAEE',
    mutedText: '#9AA3B2',
    accent: '#6C94FF',
  },
  decision: {
    allowLight: '#1B7F4B',
    allowDark: '#4CC38A',
    stepUpLight: '#9A6700',
    stepUpDark: '#E3B341',
    blockLight: '#B42318',
    blockDark: '#FF7B72',
  }
};

export const MONOSPACE_FONT = '"JetBrains Mono", monospace';

export const createAppTheme = (mode: 'light' | 'dark') => {
  const tokens = mode === 'dark' ? warrantColors.dark : warrantColors.light;
  const decision = warrantColors.decision;

  return createTheme({
    palette: {
      mode,
      background: {
        default: tokens.background,
        paper: tokens.surface,
      },
      text: {
        primary: tokens.text,
        secondary: tokens.mutedText,
      },
      primary: {
        main: tokens.accent,
      },
      divider: tokens.border,
      error: {
        main: mode === 'dark' ? decision.blockDark : decision.blockLight,
      },
      warning: {
        main: mode === 'dark' ? decision.stepUpDark : decision.stepUpLight,
      },
      success: {
        main: mode === 'dark' ? decision.allowDark : decision.allowLight,
      },
    },
    typography: {
      fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      h1: { fontWeight: 700, letterSpacing: '-0.02em' },
      h2: { fontWeight: 600, letterSpacing: '-0.01em' },
      h3: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 500 },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: tokens.background,
            color: tokens.text,
            transition: 'background-color 0.2s ease, color 0.2s ease',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundColor: tokens.raisedSurface,
            border: `1px solid ${tokens.border}`,
            backgroundImage: 'none',
            boxShadow: 'none',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: '6px',
            padding: '8px 16px',
            boxShadow: 'none',
            '&:hover': {
              boxShadow: 'none',
            },
          },
        },
      },
    },
  });
};

// Export pre-configured themes expected by App.tsx
export const darkTheme = createAppTheme('dark');
export const lightTheme = createAppTheme('light');