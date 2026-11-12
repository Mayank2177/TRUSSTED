import React, { useState, useMemo } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  Button,
  Chip,
  TextField,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
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
  Search,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XOctagon,
  FileText,
  Activity,
} from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { ILLUSTRATIVE_RUNS } from '../data/mockRuns';

export const RunDetail: React.FC = () => {
  const { runId } = useParams<{ runId?: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const prefersReducedMotion = useReducedMotion();

  // Filter & Search states for history view
  const [searchQuery, setSearchQuery] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // Find individual run if runId parameter is present
  const selectedRun = useMemo(() => {
    if (!runId) return null;
    return ILLUSTRATIVE_RUNS.find((r) => r.runId.toLowerCase() === runId.toLowerCase());
  }, [runId]);

  // Filtered runs list for history view
  const filteredRuns = useMemo(() => {
    return ILLUSTRATIVE_RUNS.filter((run) => {
      const matchesSearch =
        run.runId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        run.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
        run.productName.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesDecision = decisionFilter === 'ALL' || run.decision === decisionFilter;
      const matchesStatus = statusFilter === 'ALL' || run.executionStatus === statusFilter;

      return matchesSearch && matchesDecision && matchesStatus;
    }).sort((a, b) => {
      const dateA = new Date(a.timestamp).getTime();
      const dateB = new Date(b.timestamp).getTime();
      return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
    });
  }, [searchQuery, decisionFilter, statusFilter, sortOrder]);

  const handleClearFilters = () => {
    setSearchQuery('');
    setDecisionFilter('ALL');
    setStatusFilter('ALL');
    setSortOrder('desc');
  };

  const getDecisionChip = (decision: 'ALLOW' | 'STEP_UP' | 'BLOCK') => {
    switch (decision) {
      case 'ALLOW':
        return (
          <Chip
            icon={<CheckCircle2 size={13} />}
            label="ALLOW"
            size="small"
            sx={{
              fontWeight: 700,
              fontFamily: 'monospace',
              bgcolor: 'rgba(76,195,138,0.15)',
              color: '#4CC38A',
              borderColor: 'rgba(76,195,138,0.4)',
              border: '1px solid',
            }}
          />
        );
      case 'STEP_UP':
        return (
          <Chip
            icon={<AlertTriangle size={13} />}
            label="STEP_UP"
            size="small"
            sx={{
              fontWeight: 700,
              fontFamily: 'monospace',
              bgcolor: 'rgba(227,179,65,0.15)',
              color: '#E3B341',
              borderColor: 'rgba(227,179,65,0.4)',
              border: '1px solid',
            }}
          />
        );
      case 'BLOCK':
        return (
          <Chip
            icon={<XOctagon size={13} />}
            label="BLOCK"
            size="small"
            sx={{
              fontWeight: 700,
              fontFamily: 'monospace',
              bgcolor: 'rgba(255,123,114,0.15)',
              color: '#FF7B72',
              borderColor: 'rgba(255,123,114,0.4)',
              border: '1px solid',
            }}
          />
        );
    }
  };

  if (runId) {
    if (!selectedRun) {
      return (
        <Box sx={{ py: 8, textAlign: 'center' }}>
          <Typography variant="h5" sx={{ fontWeight: 800, mb: 2 }}>Run Not Found</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            The requested run ID "{runId}" does not exist in the illustrative demo dataset.
          </Typography>
          <Button
            variant="contained"
            component={RouterLink}
            to="/runs"
            sx={{ bgcolor: '#6C94FF', fontWeight: 700, borderRadius: 2 }}
          >
            Back to Runs History
          </Button>
        </Box>
      );
    }

    return (
      <motion.div
        initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Box sx={{ pb: 8 }}>
          {/* Back Navigation & Header */}
          <Box sx={{ mb: 3 }}>
            <Button
              startIcon={<ArrowLeft size={16} />}
              component={RouterLink}
              to="/runs"
              sx={{ color: 'text.secondary', fontWeight: 600, mb: 2, '&:hover': { bgcolor: 'action.hover' } }}
            >
              Back to Runs History
            </Button>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                  <Chip
                    label="ILLUSTRATIVE DEMO RECORD"
                    size="small"
                    sx={{ bgcolor: 'rgba(227,179,65,0.15)', color: '#E3B341', fontWeight: 800, fontFamily: 'monospace', fontSize: '11px' }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                    {selectedRun.runId}
                  </Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.03em', mb: 0.5 }}>
                  {selectedRun.productName}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Evaluated at {selectedRun.timestamp}
                </Typography>
              </Box>
              <Box>{getDecisionChip(selectedRun.decision)}</Box>
            </Box>
          </Box>

          {/* Limitations Warning Banner */}
          <Alert severity="warning" variant="outlined" sx={{ mb: 4, borderRadius: 3, bgcolor: 'rgba(227,179,65,0.05)', borderColor: 'rgba(227,179,65,0.4)' }}>
            <AlertTitle sx={{ fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
              Illustrative Telemetry Notice
            </AlertTitle>
            This inspection view displays mock evaluation telemetry. Receipt records and validation checks are illustrative and do not represent live backend execution or verified cryptographic proofs.
          </Alert>

          {/* A. Run Overview Card */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 2.5 }}>Run Overview</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
              <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 50%' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Evaluation Query</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5 }}>{selectedRun.query}</Typography>
              </Box>
              <Box sx={{ flex: { xs: '1 1 calc(50% - 12px)', md: '1 1 20%' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Execution Status</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5, fontFamily: 'monospace' }}>{selectedRun.executionStatus}</Typography>
              </Box>
              <Box sx={{ flex: { xs: '1 1 calc(50% - 12px)', md: '1 1 20%' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Timestamp</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5, fontFamily: 'monospace' }}>{selectedRun.timestamp}</Typography>
              </Box>
            </Box>
          </Card>

          {/* B. Decision Explanation */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>Decision Explanation & Reason Codes</Typography>
            <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 3 }}>
              {selectedRun.explanation}
            </Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Reason Codes</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 3 }}>
              {selectedRun.reasonCodes.map((code, idx) => (
                <Chip key={idx} label={code} size="small" sx={{ fontFamily: 'monospace', fontWeight: 700, bgcolor: 'action.hover', border: '1px solid', borderColor: 'divider' }} />
              ))}
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Evidence References</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {selectedRun.evidenceReferences.map((ref, idx) => (
                <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1.5, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                  <FileText size={16} color="#6C94FF" />
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>{ref}</Typography>
                </Box>
              ))}
            </Box>
          </Card>

          {/* C. Seven-Stage Execution Pipeline */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5 }}>Seven-Stage Evaluation Pipeline</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Execution telemetry across deterministic verification stages (Illustrative data)</Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {selectedRun.stages.map((stage) => (
                <Box key={stage.stepNumber} sx={{ p: 2.5, borderRadius: 3, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Chip label={`Stage ${stage.stepNumber}`} size="small" sx={{ fontFamily: 'monospace', fontWeight: 800, bgcolor: 'rgba(108,148,255,0.15)', color: '#6C94FF' }} />
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{stage.name}</Typography>
                    </Box>
                    <Chip
                      label={stage.status}
                      size="small"
                      sx={{
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        bgcolor: stage.status === 'Completed' ? 'rgba(76,195,138,0.15)' : stage.status === 'Skipped' ? 'action.hover' : 'rgba(255,123,114,0.15)',
                        color: stage.status === 'Completed' ? '#4CC38A' : stage.status === 'Skipped' ? 'text.secondary' : '#FF7B72',
                      }}
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: stage.details ? 1.5 : 0 }}>
                    {stage.summary}
                  </Typography>
                  {stage.details && (
                    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 1, pt: 1, borderTop: '1px dashed', borderColor: 'divider' }}>
                      {stage.details.map((det, dIdx) => (
                        <Typography key={dIdx} variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                          <strong>{det.label}:</strong> {det.value}
                        </Typography>
                      ))}
                    </Box>
                  )}
                </Box>
              ))}
            </Box>
          </Card>

          {/* D. Evidence Inspection & Source Comparison */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 2 }}>Evidence Inspection & Source Comparison</Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Extracted Product Attributes</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
              {Object.entries(selectedRun.extractedAttributes).map(([key, val], idx) => (
                <Box key={idx} sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 8px)', md: '1 1 calc(25% - 12px)' }, p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>{key}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700, mt: 0.5, fontFamily: 'monospace' }}>{val}</Typography>
                </Box>
              ))}
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Reference-Source Comparison</Typography>
            <TableContainer sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 3 }}>
              <Table size="small">
                <TableHead sx={{ bgcolor: 'background.default' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>Source Name</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Claimed Value</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Verified Value</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>Match Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {selectedRun.sourceComparison.map((comp, idx) => (
                    <TableRow key={idx}>
                      <TableCell sx={{ fontWeight: 600, fontFamily: 'monospace' }}>{comp.sourceName}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>{comp.claimedValue}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>{comp.verifiedValue}</TableCell>
                      <TableCell>
                        <Chip
                          label={comp.match ? 'Verified Match' : 'Discrepancy'}
                          size="small"
                          sx={{
                            fontFamily: 'monospace',
                            fontWeight: 700,
                            bgcolor: comp.match ? 'rgba(76,195,138,0.15)' : 'rgba(255,123,114,0.15)',
                            color: comp.match ? '#4CC38A' : '#FF7B72',
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {selectedRun.conflictingInfo && (
              <Alert severity="error" variant="outlined" sx={{ mb: 3, borderRadius: 2 }}>
                <AlertTitle sx={{ fontWeight: 700 }}>Conflicting Information Detected</AlertTitle>
                {selectedRun.conflictingInfo}
              </Alert>
            )}

            <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Illustrative Ranking Score</Typography>
                <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: 'monospace', mt: 0.5 }}>{selectedRun.rankingScore}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Illustrative Perturbation Stability</Typography>
                <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: 'monospace', mt: 0.5 }}>{selectedRun.perturbationResult}</Typography>
              </Box>
            </Box>
          </Card>
        </Box>
      </motion.div>
    );
  }

  const totalRuns = ILLUSTRATIVE_RUNS.length;
  const allowCount = ILLUSTRATIVE_RUNS.filter((r) => r.decision === 'ALLOW').length;
  const stepUpCount = ILLUSTRATIVE_RUNS.filter((r) => r.decision === 'STEP_UP').length;
  const blockCount = ILLUSTRATIVE_RUNS.filter((r) => r.decision === 'BLOCK').length;

  return (
    <motion.div
      initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ pb: 8 }}>
        {/* Header & Subtitle */}
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', md: 'center' }, flexDirection: { xs: 'column', md: 'row' }, gap: 2 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
              <Chip label="ILLUSTRATIVE DEMO DATASET" size="small" sx={{ bgcolor: 'rgba(227,179,65,0.15)', color: '#E3B341', fontWeight: 800, fontFamily: 'monospace', fontSize: '11px' }} />
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>TRUSSTED Execution History</Typography>
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.03em', mb: 1 }}>
              Runs
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Explore and inspect shopping-agent evaluation history.
            </Typography>
          </Box>
        </Box>

        {/* Summary Cards */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
          {[
            { label: 'Total Runs', value: totalRuns, color: '#6C94FF', icon: Activity },
            { label: 'ALLOW', value: allowCount, color: '#4CC38A', icon: CheckCircle2 },
            { label: 'STEP_UP', value: stepUpCount, color: '#E3B341', icon: AlertTriangle },
            { label: 'BLOCK', value: blockCount, color: '#FF7B72', icon: XOctagon },
          ].map((card, idx) => {
            const Icon = card.icon;
            return (
              <Box key={idx} sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', lg: '1 1 calc(25% - 18px)' } }}>
                <Card sx={{ p: 3, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 3.5, height: '100%', boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      {card.label}
                    </Typography>
                    <Box sx={{ width: 36, height: 36, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: `${card.color}20`, color: card.color, border: `1px solid ${card.color}40` }}>
                      <Icon size={18} />
                    </Box>
                  </Box>
                  <Typography variant="h3" sx={{ fontWeight: 900, fontFamily: '"JetBrains Mono", monospace', color: card.color }}>
                    {card.value}
                  </Typography>
                </Card>
              </Box>
            );
          })}
        </Box>

        {/* Search and Filters Bar */}
        <Card sx={{ p: 3, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 3.5, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 300px' } }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search by Run ID or query..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <Search size={18} color={theme.palette.text.secondary} />
                      </InputAdornment>
                    ),
                  },
                }}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2.5 } }}
              />
            </Box>

            <Box sx={{ flex: { xs: '1 1 calc(50% - 8px)', sm: '1 1 200px' } }}>
              <FormControl fullWidth size="small">
                <InputLabel id="decision-filter-label">Decision</InputLabel>
                <Select
                  labelId="decision-filter-label"
                  value={decisionFilter}
                  label="Decision"
                  onChange={(e) => setDecisionFilter(e.target.value)}
                  sx={{ borderRadius: 2.5 }}
                >
                  <MenuItem value="ALL">All Decisions</MenuItem>
                  <MenuItem value="ALLOW">ALLOW</MenuItem>
                  <MenuItem value="STEP_UP">STEP_UP</MenuItem>
                  <MenuItem value="BLOCK">BLOCK</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ flex: { xs: '1 1 calc(50% - 8px)', sm: '1 1 200px' } }}>
              <FormControl fullWidth size="small">
                <InputLabel id="status-filter-label">Status</InputLabel>
                <Select
                  labelId="status-filter-label"
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                  sx={{ borderRadius: 2.5 }}
                >
                  <MenuItem value="ALL">All Statuses</MenuItem>
                  <MenuItem value="Success">Success</MenuItem>
                  <MenuItem value="Flagged">Flagged</MenuItem>
                  <MenuItem value="Rejected">Rejected</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 180px' } }}>
              <FormControl fullWidth size="small">
                <InputLabel id="sort-order-label">Sort Date</InputLabel>
                <Select
                  labelId="sort-order-label"
                  value={sortOrder}
                  label="Sort Date"
                  onChange={(e) => setSortOrder(e.target.value as 'desc' | 'asc')}
                  sx={{ borderRadius: 2.5 }}
                >
                  <MenuItem value="desc">Newest First</MenuItem>
                  <MenuItem value="asc">Oldest First</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>

          {(searchQuery || decisionFilter !== 'ALL' || statusFilter !== 'ALL' || sortOrder !== 'desc') && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
              <Button size="small" onClick={handleClearFilters} sx={{ color: 'text.secondary', fontWeight: 600 }}>
                Clear Filters
              </Button>
            </Box>
          )}
        </Card>

        {/* Runs History Table */}
        <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, overflow: 'hidden', boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
          <TableContainer>
            <Table>
              <TableHead sx={{ bgcolor: 'action.hover' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>Run ID</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Product / Evaluation Query</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Date and Time</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Final Decision</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Execution Status</TableCell>
                  <TableCell sx={{ fontWeight: 800, align: 'right' }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredRuns.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} sx={{ py: 8, textAlign: 'center' }}>
                      <Typography variant="body1" sx={{ fontWeight: 700, mb: 1 }}>No runs found matching your search or filters.</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Try clearing your filters or search query.</Typography>
                      <Button variant="outlined" size="small" onClick={handleClearFilters} sx={{ borderRadius: 2 }}>
                        Clear Filters
                      </Button>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredRuns.map((run) => (
                    <TableRow
                      key={run.runId}
                      hover
                      onClick={() => navigate(`/runs/${run.runId}`)}
                      sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                    >
                      <TableCell sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#6C94FF' }}>
                        {run.runId}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 320 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>{run.productName}</Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {run.query}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', color: 'text.secondary', fontSize: '13px' }}>
                        {run.timestamp}
                      </TableCell>
                      <TableCell>{getDecisionChip(run.decision)}</TableCell>
                      <TableCell>
                        <Chip
                          label={run.executionStatus}
                          size="small"
                          variant="outlined"
                          sx={{ fontFamily: 'monospace', fontWeight: 600, fontSize: '11px' }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          variant="outlined"
                          size="small"
                          component={RouterLink}
                          to={`/runs/${run.runId}`}
                          onClick={(e) => e.stopPropagation()}
                          sx={{ fontWeight: 700, borderRadius: 2, textTransform: 'none' }}
                        >
                          Inspect
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      </Box>
    </motion.div>
  );
};

export default RunDetail;