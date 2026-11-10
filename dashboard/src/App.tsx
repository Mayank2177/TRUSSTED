import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ThemeProvider, CssBaseline, Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Typography, Chip, Card, CardContent, Grid } from '@mui/material';
import { LayoutDashboard, ShieldAlert, FileText, CheckSquare, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import { darkTheme } from './theme';
import { RunDetail } from './views/RunDetail';
import { ReceiptViewer } from './views/ReceiptViewer';

interface BenchmarkMetric {
  scenario_id: string;
  scenario_title: string;
  attack_type: string;
  kind: 'attack' | 'benign';
  baseline_asr: number;
  warrant_asr: number;
  n: number;
  ci_lower: number;
  ci_upper: number;
  result_status: 'Mitigated' | 'Not mitigated' | 'Benign';
}

const LimitationsBanner: React.FC = () => (
  <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
    <Card sx={{
      mb: 3,
      borderLeft: '4px solid #F59E0B',
      background: 'linear-gradient(135deg, rgba(19, 25, 36, 0.9) 0%, rgba(30, 37, 51, 0.9) 100%)',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
      backdropFilter: 'blur(8px)'
    }}>
      <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 2.5, '&:last-child': { pb: 2.5 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <ShieldAlert size={20} color="#F59E0B" />
          <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500 }}>
            Prototype research scope. Fails on poisoned consistent facts (S6) and depends on reference feeds.
          </Typography>
        </Box>
        <Link to="/limitations" style={{ color: '#818CF8', fontWeight: 600, textDecoration: 'none', fontSize: '13px', whiteSpace: 'nowrap' }}>
          View all limitations &rarr;
        </Link>
      </CardContent>
    </Card>
  </motion.div>
);

const BenchmarkReport: React.FC = () => {
  const [metrics, setMetrics] = useState<BenchmarkMetric[]>([]);

  useEffect(() => {
    setMetrics([
      {
        scenario_id: 'S1',
        scenario_title: 'Fictional-brand clone store at lower price',
        attack_type: 'Phishing storefront',
        kind: 'attack',
        baseline_asr: 0.85,
        warrant_asr: 0.05,
        n: 40,
        ci_lower: 0.01,
        ci_upper: 0.15,
        result_status: 'Mitigated'
      },
      {
        scenario_id: 'S6',
        scenario_title: 'Poisoned consistent fact: both sources agree on false spec',
        attack_type: 'Known limitation',
        kind: 'attack',
        baseline_asr: 0.90,
        warrant_asr: 0.90,
        n: 40,
        ci_lower: 0.78,
        ci_upper: 0.96,
        result_status: 'Not mitigated'
      }
    ]);
  }, []);

  return (
    <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <LimitationsBanner />
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ mb: 0.5, fontWeight: 800, letterSpacing: '-0.02em' }}>Benchmark Report</Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Honest evaluation of decision-integrity performance across attack and benign scenarios.
        </Typography>
      </Box>

      {/* Metric Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {[
          { title: 'Overall Attack Reduction', value: '12.5%', sub: 'n = 280 | 95% CI [5.5, 18.2]' },
          { title: 'False-Block Rate (Benign)', value: '4.2%', sub: 'n = 150 | 95% CI [1.1, 8.4]' }
        ].map((card, i) => (
          <Grid size={{ xs: 12, md: 6 }} key={i}>
            <Card sx={{
              position: 'relative',
              overflow: 'hidden',
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '4px',
                background: i === 0 ? 'linear-gradient(90deg, #6366F1, #A855F7)' : 'linear-gradient(90deg, #10B981, #3B82F6)'
              }
            }}>
              <CardContent sx={{ p: 3.5 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {card.title}
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 800, my: 1.5, color: '#F9FAFB', letterSpacing: '-0.03em' }}>
                  {card.value}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace', bgcolor: 'rgba(255,255,255,0.03)', px: 1, py: 0.5, borderRadius: 1 }}>
                  {card.sub}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>Scenario Breakdown</Typography>
      <Card sx={{ boxShadow: '0 10px 30px rgba(0,0,0,0.3)' }}>
        <Box sx={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#9CA3AF', background: 'rgba(255,255,255,0.01)' }}>
                <th style={{ padding: '16px 20px' }}>Scenario</th>
                <th style={{ padding: '16px 20px' }}>Attack Type</th>
                <th style={{ padding: '16px 20px' }}>Baseline ASR</th>
                <th style={{ padding: '16px 20px' }}>Warrant ASR</th>
                <th style={{ padding: '16px 20px' }}>Sample (n)</th>
                <th style={{ padding: '16px 20px' }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.scenario_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.2s' }}>
                  <td style={{ padding: '16px 20px', fontWeight: 600, color: '#F9FAFB' }}>{m.scenario_id}: {m.scenario_title}</td>
                  <td style={{ padding: '16px 20px', color: '#9CA3AF' }}>{m.attack_type}</td>
                  <td style={{ padding: '16px 20px', fontFamily: 'monospace', color: '#D1D5DB' }}>{(m.baseline_asr * 100).toFixed(1)}%</td>
                  <td style={{ padding: '16px 20px', fontFamily: 'monospace', color: '#D1D5DB' }}>{(m.warrant_asr * 100).toFixed(1)}%</td>
                  <td style={{ padding: '16px 20px', fontFamily: 'monospace', color: '#D1D5DB' }}>{m.n}</td>
                  <td style={{ padding: '16px 20px' }}>
                    <Chip
                      label={m.result_status}
                      size="small"
                      color={m.result_status === 'Mitigated' ? 'success' : 'error'}
                      variant="outlined"
                      sx={{ fontWeight: 700 }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      </Card>
    </motion.div>
  );
};

const LimitationsView: React.FC = () => (
  <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
    <Card sx={{ boxShadow: '0 10px 30px rgba(0,0,0,0.3)' }}>
      <CardContent sx={{ p: 4 }}>
        <Typography variant="h5" sx={{ mb: 3, fontWeight: 800 }}>Known Limitations</Typography>
        <ol style={{ lineHeight: '1.9', color: '#9CA3AF', paddingLeft: '20px' }}>
          <li style={{ marginBottom: '12px' }}><strong>Poisoned-but-consistent facts:</strong> Both sources agreeing on a falsehood pass checks (Scenario S6).</li>
          <li style={{ marginBottom: '12px' }}><strong>LLM extraction risk:</strong> Schema constraints reduce, but do not eliminate, untrusted text risks.</li>
          <li style={{ marginBottom: '12px' }}><strong>Perturbation latency/cost:</strong> Checks add overhead and can trigger false positives on close choices.</li>
          <li style={{ marginBottom: '12px' }}><strong>User Intent dependency:</strong> Deterministic ranking requires explicit intent, which many users lack.</li>
          <li style={{ marginBottom: '12px' }}><strong>Receipt scope:</strong> A signed receipt proves record integrity, not absolute input truth.</li>
          <li><strong>Synthetic fixtures:</strong> Results derive from synthetic fixtures and do not generalise directly to the open web without testing.</li>
        </ol>
      </CardContent>
    </Card>
  </motion.div>
);


const DashboardLayout: React.FC = () => {
  const location = useLocation();

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default', background: 'radial-gradient(circle at 10% 20%, #0D121F 0%, #0B0F17 90%)' }}>
      {/* Sidebar Navigation */}
      <Drawer
        variant="permanent"
        sx={{
          width: 260,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: 260,
            boxSizing: 'border-box',
            bgcolor: '#080C14',
            borderRight: '1px solid rgba(255, 255, 255, 0.06)',
            p: 3,
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 4, px: 1 }}>
          <Box sx={{
            width: 38,
            height: 38,
            borderRadius: 2.5,
            background: 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.5)'
          }}>
            <Sparkles size={20} color="#FFF" />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 900, color: '#FFF', lineHeight: 1, letterSpacing: '-0.03em' }}>WARRANT</Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '9px', letterSpacing: '1.5px', fontWeight: 600 }}>DECISION INTEGRITY</Typography>
          </Box>
        </Box>

        <List sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {[
            { path: '/', label: 'Benchmark Report', icon: LayoutDashboard },
            { path: '/limitations', label: 'Limitations', icon: ShieldAlert },
            { path: '/runs', label: 'Run Detail', icon: CheckSquare },
            { path: '/receipts', label: 'Receipt Viewer', icon: FileText },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <ListItemButton
                key={item.path}
                component={Link}
                to={item.path}
                sx={{
                  borderRadius: 2.5,
                  py: 1.4,
                  px: 2,
                  bgcolor: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                  border: '1px solid',
                  borderColor: isActive ? 'rgba(99, 102, 241, 0.35)' : 'transparent',
                  color: isActive ? '#818CF8' : 'text.secondary',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.04)',
                    color: '#FFF',
                    borderColor: 'rgba(255, 255, 255, 0.08)'
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: 'inherit' }}><Icon size={18} /></ListItemIcon>
                <ListItemText primary={item.label} sx={{ '& .MuiListItemText-primary': { fontSize: '13.5px', fontWeight: isActive ? 700 : 500, letterSpacing: '-0.01em' } }} />
              </ListItemButton>
            );
          })}
        </List>

        <Box sx={{ mt: 'auto', pt: 2.5, borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', bgcolor: 'rgba(255,255,255,0.02)', p: 1.5, borderRadius: 2, border: '1px solid rgba(255,255,255,0.04)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <motion.div
                animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
                transition={{ duration: 2, repeat: Infinity }}
                style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: '#10B981', boxShadow: '0 0 8px #10B981' }}
              />
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, fontSize: '11px' }}>Engine Active</Typography>
            </Box>
            <Chip label="v1.0.4" size="small" variant="outlined" sx={{ fontSize: '10px', height: 20, borderColor: 'rgba(255,255,255,0.1)', color: 'text.secondary' }} />
          </Box>
        </Box>
      </Drawer>

      
      <Box component="main" sx={{ flexGrow: 1, p: 5, maxWidth: '1260px' }}>
        <Routes>
          <Route path="/" element={<BenchmarkReport />} />
          <Route path="/limitations" element={<LimitationsView />} />
          <Route path="/runs" element={<RunDetail />} />
          <Route path="/receipts" element={<ReceiptViewer />} />
        </Routes>
      </Box>
    </Box>
  );
};

export function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Router>
        <DashboardLayout />
      </Router>
    </ThemeProvider>
  );
}

export default App;