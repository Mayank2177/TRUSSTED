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
  ShieldCheck,
  Link as LinkIcon,
  Key,
  Database,
  ExternalLink,
} from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { ILLUSTRATIVE_RECEIPTS, ReceiptRecord } from '../data/mockReceipts';

export const ReceiptViewer: React.FC = () => {
  const { receiptId } = useParams<{ receiptId?: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const prefersReducedMotion = useReducedMotion();

  // Search and filter state for history view
  const [searchQuery, setSearchQuery] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');

  // Find individual receipt if receiptId parameter is present
  const selectedReceipt = useMemo(() => {
    if (!receiptId) return null;
    return ILLUSTRATIVE_RECEIPTS.find((r) => r.receiptId.toLowerCase() === receiptId.toLowerCase());
  }, [receiptId]);

  // Filtered receipts list
  const filteredReceipts = useMemo(() => {
    return ILLUSTRATIVE_RECEIPTS.filter((rcpt) => {
      const matchesSearch =
        rcpt.receiptId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rcpt.runId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rcpt.productName.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesDecision = decisionFilter === 'ALL' || rcpt.decision === decisionFilter;

      return matchesSearch && matchesDecision;
    });
  }, [searchQuery, decisionFilter]);

  const handleClearFilters = () => {
    setSearchQuery('');
    setDecisionFilter('ALL');
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

  if (receiptId) {
    if (!selectedReceipt) {
      return (
        <Box sx={{ py: 8, textAlign: 'center' }}>
          <Typography variant="h5" sx={{ fontWeight: 800, mb: 2 }}>Receipt Not Found</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            The requested receipt ID "{receiptId}" does not exist in the illustrative demo dataset.
          </Typography>
          <Button
            variant="contained"
            component={RouterLink}
            to="/receipts"
            sx={{ bgcolor: '#6C94FF', fontWeight: 700, borderRadius: 2 }}
          >
            Back to Receipts History
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
              to="/receipts"
              sx={{ color: 'text.secondary', fontWeight: 600, mb: 2, '&:hover': { bgcolor: 'action.hover' } }}
            >
              Back to Receipts History
            </Button>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                  <Chip
                    label="ILLUSTRATIVE DEMO RECEIPT"
                    size="small"
                    sx={{ bgcolor: 'rgba(227,179,65,0.15)', color: '#E3B341', fontWeight: 800, fontFamily: 'monospace', fontSize: '11px' }}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                    {selectedReceipt.receiptId}
                  </Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.03em', mb: 0.5 }}>
                  {selectedReceipt.productName}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Associated Run: <RouterLink to={`/runs/${selectedReceipt.runId}`} style={{ color: '#6C94FF', fontWeight: 600, textDecoration: 'none' }}>{selectedReceipt.runId}</RouterLink>
                </Typography>
              </Box>
              <Box>{getDecisionChip(selectedReceipt.decision)}</Box>
            </Box>
          </Box>

          {/* Verification Limitations Notice */}
          <Alert severity="warning" variant="outlined" sx={{ mb: 4, borderRadius: 3, bgcolor: 'rgba(227,179,65,0.05)', borderColor: 'rgba(227,179,65,0.4)' }}>
            <AlertTitle sx={{ fontWeight: 800, fontFamily: '"JetBrains Mono", monospace' }}>
              Verification & Data Integrity Notice
            </AlertTitle>
            This cryptographic receipt record is illustrative. Receipt integrity and signature binding confirm log consistency but <strong>do not establish the absolute truthfulness</strong> of the original product information or merchant listing claims.
          </Alert>

          {/* Verification Panel */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
              <ShieldCheck size={22} color="#4CC38A" />
              <Typography variant="h6" sx={{ fontWeight: 800 }}>Verification Panel</Typography>
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Signature Status</Typography>
                  <Typography variant="body1" sx={{ fontWeight: 700, color: '#4CC38A', fontFamily: 'monospace', mt: 0.5 }}>{selectedReceipt.verificationStatus}</Typography>
                </Box>
                <Chip label={selectedReceipt.algorithm} size="small" variant="outlined" sx={{ fontFamily: 'monospace', fontWeight: 600 }} />
              </Box>

              <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Digital Signature</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600, mt: 0.5, wordBreak: 'break-all' }}>{selectedReceipt.signature}</Typography>
              </Box>

              <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Public Key Metadata</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600, mt: 0.5, wordBreak: 'break-all' }}>{selectedReceipt.publicKey}</Typography>
              </Box>
            </Box>
          </Card>

          {/* Hash-Chain Visualization */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
              <LinkIcon size={22} color="#6C94FF" />
              <Typography variant="h6" sx={{ fontWeight: 800 }}>Hash-Chain Visualization</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Demonstrating tamper-evident chaining: each receipt cryptographically references the hash of the preceding event in the audit sequence.
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ p: 2.5, borderRadius: 3, bgcolor: 'background.default', border: '1px dashed', borderColor: 'divider' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Previous Receipt Hash (Parent)</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 700, color: 'text.primary', mt: 0.5, wordBreak: 'break-all' }}>
                  {selectedReceipt.previousReceiptHash}
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <Box sx={{ width: 2, height: 24, bgcolor: 'primary.main' }} />
              </Box>

              <Box sx={{ p: 2.5, borderRadius: 3, bgcolor: 'rgba(108,148,255,0.08)', border: '1px solid', borderColor: 'rgba(108,148,255,0.3)' }}>
                <Typography variant="caption" color="primary.main" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Current Receipt Payload Hash (This Record)</Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 700, color: 'text.primary', mt: 0.5, wordBreak: 'break-all' }}>
                  {selectedReceipt.payloadHash}
                </Typography>
              </Box>
            </Box>
          </Card>

          {/* Associated Run & Payload Metadata */}
          <Card sx={{ p: 3.5, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mb: 2.5 }}>Receipt Metadata & Run Context</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 3 }}>
              <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 50%' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Evaluation Query</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5 }}>{selectedReceipt.query}</Typography>
              </Box>
              <Box sx={{ flex: { xs: '1 1 calc(50% - 12px)', md: '1 1 20%' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Timestamp</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5, fontFamily: 'monospace' }}>{selectedReceipt.timestamp}</Typography>
              </Box>
              <Box sx={{ flex: { xs: '1 1 calc(50% - 12px)', md: '1 1 20%' } }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>Associated Run</Typography>
                <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.5, fontFamily: 'monospace' }}>
                  <RouterLink to={`/runs/${selectedReceipt.runId}`} style={{ color: '#6C94FF', textDecoration: 'none' }}>{selectedReceipt.runId}</RouterLink>
                </Typography>
              </Box>
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Reason Codes</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 3 }}>
              {selectedReceipt.reasonCodes.map((code, idx) => (
                <Chip key={idx} label={code} size="small" sx={{ fontFamily: 'monospace', fontWeight: 700, bgcolor: 'action.hover', border: '1px solid', borderColor: 'divider' }} />
              ))}
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Evidence References</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {selectedReceipt.evidenceReferences.map((ref, idx) => (
                <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1.5, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                  <FileText size={16} color="#6C94FF" />
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>{ref}</Typography>
                </Box>
              ))}
            </Box>
          </Card>
        </Box>
      </motion.div>
    );
  }

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
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>TRUSSTED Cryptographic Audit Log</Typography>
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.03em', mb: 1 }}>
              Receipts
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Inspect immutable evaluation receipts and hash-chained audit trails.
            </Typography>
          </Box>
        </Box>

        {/* Search and Filters Bar */}
        <Card sx={{ p: 3, mb: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 3.5, boxShadow: '0 8px 32px rgba(0,0,0,0.08)' }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
            <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 350px' } }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search by Receipt ID, Run ID, or product..."
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

            <Box sx={{ flex: { xs: '1 1 100%', sm: '1 1 220px' } }}>
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
          </Box>

          {(searchQuery || decisionFilter !== 'ALL') && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
              <Button size="small" onClick={handleClearFilters} sx={{ color: 'text.secondary', fontWeight: 600 }}>
                Clear Filters
              </Button>
            </Box>
          )}
        </Card>

        {/* Receipts History Table */}
        <Card sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 4, overflow: 'hidden', boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
          <TableContainer>
            <Table>
              <TableHead sx={{ bgcolor: 'action.hover' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 800 }}>Receipt ID</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Associated Run</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Timestamp</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Final Decision</TableCell>
                  <TableCell sx={{ fontWeight: 800 }}>Verification Status</TableCell>
                  <TableCell sx={{ fontWeight: 800, align: 'right' }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredReceipts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} sx={{ py: 8, textAlign: 'center' }}>
                      <Typography variant="body1" sx={{ fontWeight: 700, mb: 1 }}>No receipts found matching your search or filters.</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Try clearing your search query or decision filter.</Typography>
                      <Button variant="outlined" size="small" onClick={handleClearFilters} sx={{ borderRadius: 2 }}>
                        Clear Filters
                      </Button>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredReceipts.map((rcpt) => (
                    <TableRow
                      key={rcpt.receiptId}
                      hover
                      onClick={() => navigate(`/receipts/${rcpt.receiptId}`)}
                      sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                    >
                      <TableCell sx={{ fontWeight: 800, fontFamily: 'monospace', color: '#6C94FF' }}>
                        {rcpt.receiptId}
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                        {rcpt.runId}
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', color: 'text.secondary', fontSize: '13px' }}>
                        {rcpt.timestamp}
                      </TableCell>
                      <TableCell>{getDecisionChip(rcpt.decision)}</TableCell>
                      <TableCell>
                        <Chip
                          label={rcpt.verificationStatus}
                          size="small"
                          variant="outlined"
                          sx={{ fontFamily: 'monospace', fontWeight: 600, fontSize: '11px', color: '#4CC38A', borderColor: 'rgba(76,195,138,0.4)' }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          variant="outlined"
                          size="small"
                          component={RouterLink}
                          to={`/receipts/${rcpt.receiptId}`}
                          onClick={(e) => e.stopPropagation()}
                          sx={{ fontWeight: 700, borderRadius: 2, textTransform: 'none' }}
                        >
                          View Details
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

export default ReceiptViewer;