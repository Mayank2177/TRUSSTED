import React, { useState } from 'react';
import { Box, Drawer, AppBar, Toolbar, Typography, List, ListItem, ListItemButton, ListItemIcon, ListItemText, IconButton, useMediaQuery, useTheme } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import PlayArrowOutlinedIcon from '@mui/icons-material/PlayArrowOutlined';
import AssessmentOutlinedIcon from '@mui/icons-material/AssessmentOutlined';
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useThemeContext } from '../../context/ThemeContext';

interface AppLayoutProps {
  children: React.ReactNode;
  currentView: string;
  onViewChange: (view: string) => void;
}

const DRAWER_WIDTH = 260;

const navItems = [
  { id: 'overview', label: 'Overview', icon: <DashboardOutlinedIcon fontSize="small" /> },
  { id: 'runs', label: 'Runs', icon: <PlayArrowOutlinedIcon fontSize="small" /> },
  { id: 'benchmark', label: 'Benchmark', icon: <AssessmentOutlinedIcon fontSize="small" /> },
  { id: 'receipts', label: 'Receipts', icon: <ReceiptLongOutlinedIcon fontSize="small" /> },
  { id: 'limitations', label: 'Limitations', icon: <InfoOutlinedIcon fontSize="small" /> },
];

export const AppLayout: React.FC<AppLayoutProps> = ({ children, currentView, onViewChange }) => {
  const theme = useTheme();
  const { mode, toggleTheme } = useThemeContext();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider' }}>
      <Toolbar sx={{ px: 3, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: '-0.01em' }}>
          TRUSSTED 
        </Typography>
        <Box
          component="span"
          sx={{
            px: 1,
            py: 0.25,
            fontSize: '0.7rem',
            fontWeight: 600,
            borderRadius: 1,
            backgroundColor: theme.palette.action.selected,
            color: theme.palette.text.secondary,
          }}
        >
          v1.0
        </Box>
      </Toolbar>
      <List sx={{ px: 2, py: 1, flex: 1 }}>
        {navItems.map((item) => {
          const selected = currentView === item.id;
          return (
            <ListItem key={item.id} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                selected={selected}
                onClick={() => {
                  onViewChange(item.id);
                  if (isMobile) setMobileOpen(false);
                }}
                sx={{
                  borderRadius: 1.5,
                  py: 1,
                  px: 2,
                  '&.Mui-selected': {
                    backgroundColor: theme.palette.action.selected,
                    color: theme.palette.primary.main,
                    fontWeight: 600,
                    '& .MuiListItemIcon-root': {
                      color: theme.palette.primary.main,
                    },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: theme.palette.text.secondary }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography sx={{ fontSize: '0.9rem', fontWeight: selected ? 600 : 500 }}>
                      {item.label}
                    </Typography>
                  }
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', backgroundColor: 'background.default' }}>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { md: `${DRAWER_WIDTH}px` },
          backgroundColor: theme.palette.background.default,
          borderBottom: `1px solid ${theme.palette.divider}`,
          color: theme.palette.text.primary,
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between', px: { xs: 2, md: 4 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {isMobile && (
              <IconButton color="inherit" aria-label="open drawer" edge="start" onClick={handleDrawerToggle}>
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="subtitle1" sx={{ fontWeight: 600, textTransform: 'capitalize' }}>
              {navItems.find((i) => i.id === currentView)?.label || currentView}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton onClick={toggleTheme} color="inherit" aria-label="toggle theme">
              {mode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        {isMobile ? (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{ keepMounted: true }}
            sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH } }}
          >
            {drawerContent}
          </Drawer>
        ) : (
          <Drawer
            variant="permanent"
            sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH, borderRight: '1px solid', borderColor: 'divider' } }}
            open
          >
            {drawerContent}
          </Drawer>
        )}
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: 3, width: { md: `calc(100% - ${DRAWER_WIDTH}px)` }, mt: '64px', bgcolor: 'background.default', minHeight: 'calc(100vh - 64px)' }}>
        {children}
      </Box>
    </Box>
  );
};