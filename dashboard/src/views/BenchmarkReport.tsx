import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  Button,
  Chip,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  AlertTitle,
  useTheme,
} from '@mui/material';
import {
  ShieldAlert,
  BarChart2,
  Layers,
  RefreshCw,
  Info,
} from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { ILLUSTRATIVE_BENCHMARK_METRICS, ILLUSTRATIVE_SCENARIOS } from '../data/mockBenchmarks';

export const BenchmarkReport: React.FC = () => {
  const theme = useTheme();
  const prefersReducedMotion = useReducedMotion();
  const [tabIndex, setTabIndex] = useState(0);

  const adversarialScenarios = ILLUSTRATIVE_SCENARIOS.filter((s) => s.category === 'Adversarial');
  const benignScenarios = ILLUSTRATIVE_SCENARIOS.filter((s) => s.category === 'Benign');

  return (
    <motion.div
      initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ width: '100%', pb: 8 }}>

        {/* Header Section */}
        <Box sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', md: 'center' },
          flexDirection: { xs: 'column', md: 'row' },
          gap: 2,
          mb: 4,
          p: 4,
          background: 'linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(30,41,59,0.95) 100%)',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 4,
          boxShadow: '0 10px 40px rgba(0,0,0,0.3)'
        }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
              <Chip label="ILLUSTRATIVE DEMO DATA" size="small" sx={{ bgcolor: 'rgba(227,179,65,0.15)', color: '#E3B341', fontWeight: 800, fontFamily: 'monospace' }} />
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>TRUSSTED Evaluation Harness</Typography>
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.03em', mb: 1 }}>
              Benchmark & Evaluation
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: '700px' }}>
              Measure how TRUSSTED responds to adversarial shopping-agent scenarios and benign product-evaluation tasks. Actual benchmark results will be populated after backend evaluation runs are integrated.
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<RefreshCw size={16} />}
            sx={{ fontWeight: 700, borderRadius: 2.5, borderColor: 'divider', color: 'text.primary' }}
            onClick={() => window.location.reload()}
          >
            Reset Metrics
          </Button>
        </Box>

        <Alert severity="warning" variant="outlined" sx={{ mb: 4, borderRadius: 3, bgcolor: 'rgba(227, 179, 65, 0.05)', borderColor: 'rgba(227, 179, 65, 0.4)' }}>
          <AlertTitle sx={{ fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
            Known Limitation: S6 — Poisoned-but-consistent facts
          </AlertTitle>
          TRUSSTED may fail when misleading information remains internally consistent across all available primary and secondary evidence sources. Cross-checking alone cannot detect anomalies if all available reference feeds are uniformly compromised.
        </Alert>

        {/* Navigation Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 4 }}>
          <Tabs
            value={tabIndex}
            onChange={(_, val) => setTabIndex(val)}
            sx={{ '& .MuiTab-root': { fontWeight: 700, fontSize: '14px', textTransform: 'none', minHeight: 48 } }}
          >
            <Tab label="Summary Metrics" icon={<BarChart2 size={16} />} iconPosition="start" />
            <Tab label="Scenario Evaluation (S1–S7 & B1–B5)" icon={<Layers size={16} />} iconPosition="start" />
            <Tab label="Methodology & Limitations" icon={<Info size={16} />} iconPosition="start" />
          </Tabs>
        </Box>

        {tabIndex === 0 && (
          <Box>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, gap: 3, mb: 4 }}>
              {ILLUSTRATIVE_BENCHMARK_METRICS.map((metric, idx) => (
                <Card key={idx} sx={{ p: 3, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 3.5, height: '100%', boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      {metric.name}
                    </Typography>
                    <Chip label="Illustrative" size="small" sx={{ height: 20, fontSize: '10px', fontFamily: 'monospace', bgcolor: 'rgba(227,179,65,0.1)', color: '#E3B341', fontWeight: 700 }} />
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 900, mb: 1, fontFamily: '"JetBrains Mono", monospace', color: 'text.primary' }}>
                    {metric.value}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: '40px' }}>
                    {metric.definition}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                    {metric.sampleSize && (
                      <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary', bgcolor: 'action.hover', px: 1, py: 0.5, borderRadius: 1 }}>
                        n = {metric.sampleSize}
                      </Typography>
                    )}
                    {metric.confidenceInterval && (
                      <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary', bgcolor: 'action.hover', px: 1, py: 0.5, borderRadius: 1 }}>
                        95% CI: {metric.confidenceInterval}
                      </Typography>
                    )}
                  </Box>
                </Card>
              ))}
            </Box>
          </Box>
        )}

        {tabIndex === 1 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Card sx={{ p: 3.5, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4 }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>Adversarial Scenarios (S1 — S7)</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Evaluating system resilience against prompt injection, phishing storefronts, metadata manipulation, and poisoned consistency feeds.
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead sx={{ bgcolor: 'action.hover' }}>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 800 }}>ID</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Scenario Name & Description</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Expected Behavior</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Measured Result (Demo)</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {adversarialScenarios.map((s) => (
                      <TableRow key={s.id} sx={{ '&:hover': { bgcolor: 'action.hover' } }}>
                        <TableCell sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#6C94FF' }}>{s.id}</TableCell>
                        <TableCell>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>{s.name}</Typography>
                          <Typography variant="caption" color="text.secondary">{s.description}</Typography>
                        </TableCell>
                        <TableCell sx={{ fontSize: '13px', color: 'text.secondary' }}>{s.expectedBehavior}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontWeight: 700, color: s.isKnownLimitation ? '#FF7B72' : '#4CC38A' }}>
                          {s.measuredResult}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={s.status}
                            size="small"
                            sx={{
                              fontWeight: 700,
                              fontFamily: 'monospace',
                              bgcolor: s.status === 'Mitigated' ? 'rgba(76,195,138,0.15)' : 'rgba(255,123,114,0.15)',
                              color: s.status === 'Mitigated' ? '#4CC38A' : '#FF7B72',
                            }}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Card>

            <Card sx={{ p: 3.5, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4 }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>Benign Scenarios (B1 — B5)</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Evaluating baseline accuracy and false-block rates on legitimate consumer tasks.
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead sx={{ bgcolor: 'action.hover' }}>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 800 }}>ID</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Scenario Name & Description</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Expected Behavior</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Measured Result (Demo)</TableCell>
                      <TableCell sx={{ fontWeight: 800 }}>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {benignScenarios.map((s) => (
                      <TableRow key={s.id} sx={{ '&:hover': { bgcolor: 'action.hover' } }}>
                        <TableCell sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#6C94FF' }}>{s.id}</TableCell>
                        <TableCell>
                          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>{s.name}</Typography>
                          <Typography variant="caption" color="text.secondary">{s.description}</Typography>
                        </TableCell>
                        <TableCell sx={{ fontSize: '13px', color: 'text.secondary' }}>{s.expectedBehavior}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontWeight: 700, color: '#4CC38A' }}>
                          {s.measuredResult}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={s.status}
                            size="small"
                            sx={{ fontWeight: 700, fontFamily: 'monospace', bgcolor: 'rgba(76,195,138,0.15)', color: '#4CC38A' }}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Card>
          </Box>
        )}

        {tabIndex === 2 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Card sx={{ p: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4 }}>
              <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>Evaluation Methodology</Typography>
              <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 3 }}>
                TRUSSTED benchmarks quantify shopping agent security across two distinct test categories: <b>Adversarial</b> and <b>Benign</b>. Attack Success Rate (ASR) measures vulnerability to malicious manipulation, while False-Block Rate measures operational friction on standard user queries.
              </Typography>
            </Card>

            <Card sx={{ p: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'rgba(227,179,65,0.4)', borderRadius: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <ShieldAlert size={28} color="#E3B341" />
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 900 }}>S6 — Poisoned-but-consistent facts (Known Limitation)</Typography>
                  <Typography variant="body2" color="text.secondary">Deep dive into the theoretical boundary of automated evidence cross-checking.</Typography>
                </Box>
              </Box>
              <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 3 }}>
                Scenario 6 (S6) represents a fundamental boundary in automated evidence verification: if an advanced adversary simultaneously compromises both primary merchant listings and independent secondary registries with identical false assertions, TRUSSTED's cross-check stage will find 100% internal consistency between feeds and incorrectly issue an ALLOW decision.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                Conclusion: Automated cross-checking alone cannot solve coordinated upstream falsehoods. Human review and out-of-band physical verification remain essential for high-risk transactions.
              </Typography>
            </Card>
          </Box>
        )}

      </Box>
    </motion.div>
  );
};

export default BenchmarkReport;