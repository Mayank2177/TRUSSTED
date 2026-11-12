import React, { useState } from 'react';
import { Box, Button, Container, Grid, Typography, Card, CardContent, Chip } from '@mui/material';
import { ArrowRight, Cpu, Sparkles, Network, Search, CheckSquare, ShieldAlert, Lock, Key, Star, ShieldCheck, Activity, Unlock, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LandingViewProps {
  onNavigateToLogin: () => void;
  onNavigateToSignup: () => void;
  onNavigateToDashboard: () => void;
}

export const LandingView: React.FC<LandingViewProps> = ({
  onNavigateToLogin,
  onNavigateToSignup,
  onNavigateToDashboard,
}) => {
  const [activeNode, setActiveNode] = useState<string>('Hover a node to inspect telemetry');
  const [morphIndex, setMorphIndex] = useState<number>(0);

  const morphIcons = [
    { icon: Lock, label: 'Secured Enclave', color: '#6C94FF', glow: 'rgba(108,148,255,0.4)' },
    { icon: Key, label: 'Access Token', color: '#E3B341', glow: 'rgba(227,179,65,0.4)' },
    { icon: Star, label: 'Integrity Verified', color: '#EC4899', glow: 'rgba(236,72,153,0.4)' },
    { icon: ShieldCheck, label: 'Zero-Trust Gate', color: '#4CC38A', glow: 'rgba(76,195,138,0.4)' },
    { icon: Unlock, label: 'Dynamic Decrypt', color: '#38BDF8', glow: 'rgba(56,189,248,0.4)' }
  ];

  React.useEffect(() => {
    const interval = setInterval(() => {
      setMorphIndex((prev) => (prev + 1) % morphIcons.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const CurrentIconComponent = morphIcons[morphIndex].icon;
  const currentAccent = morphIcons[morphIndex].color;
  const currentGlow = morphIcons[morphIndex].glow;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', color: 'text.primary', pb: 12, overflowX: 'hidden', position: 'relative' }}>

        <motion.div
          initial={{ y: -30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 1100,
            backdropFilter: 'blur(16px)',
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            borderBottom: '1px solid rgba(108, 148, 255, 0.25)',
            boxShadow: '0 4px 30px rgba(108, 148, 255, 0.15)'
          }}
        >
          <Container maxWidth="lg" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer' }} onClick={onNavigateToDashboard}>
              <motion.div animate={{ rotate: [0, 360] }} transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}>
                <ShieldCheck size={26} color="#6C94FF" />
              </motion.div>
              <Typography variant="h6" sx={{ fontWeight: 900, letterSpacing: '-0.03em', background: 'linear-gradient(135deg, #6C94FF 0%, #4CC38A 50%, #EC4899 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                TRUSSTED
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={onNavigateToLogin}
                  sx={{ borderColor: 'rgba(108,148,255,0.4)', color: 'text.primary', fontWeight: 700, px: 2.5, py: 1, borderRadius: 2, '&:hover': { bgcolor: 'rgba(108,148,255,0.1)', borderColor: '#6C94FF' } }}
                >
                  Sign In
                </Button>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  variant="contained"
                  size="small"
                  onClick={onNavigateToSignup}
                  sx={{ bgcolor: '#6C94FF', fontWeight: 700, px: 2.5, py: 1, borderRadius: 2, boxShadow: '0 0 20px rgba(108,148,255,0.4)', '&:hover': { bgcolor: '#5275e0' } }}
                >
                  Sign Up
                </Button>
              </motion.div>
            </Box>
          </Container>
        </motion.div>

        <Container maxWidth="lg" sx={{ pt: 22, pb: 6, textAlign: 'center', position: 'relative' }}>

          <Box sx={{ position: 'absolute', top: 40, left: '5%', pointerEvents: 'none', display: { xs: 'none', md: 'block' }, zIndex: 1 }}>
            <motion.div
              animate={{ y: [-15, 15, -15], rotate: [0, 15, -15, 0], scale: [1, 1.15, 1] }}
              transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Card sx={{ p: 3, borderRadius: 4, background: 'linear-gradient(135deg, rgba(108,148,255,0.15) 0%, rgba(236,72,153,0.05) 100%)', border: '1px solid rgba(108,148,255,0.3)', boxShadow: '0 0 30px rgba(108,148,255,0.2)' }}>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={morphIndex}
                    initial={{ scale: 0.5, opacity: 0, rotate: -45 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    exit={{ scale: 0.5, opacity: 0, rotate: 45 }}
                    transition={{ duration: 0.4 }}
                  >
                    <CurrentIconComponent size={56} color={currentAccent} style={{ filter: `drop-shadow(0 0 20px ${currentGlow})` }} />
                  </motion.div>
                </AnimatePresence>
              </Card>
            </motion.div>
          </Box>

          <Box sx={{ position: 'absolute', top: 80, right: '5%', pointerEvents: 'none', display: { xs: 'none', md: 'block' }, zIndex: 1 }}>
            <motion.div
              animate={{ y: [15, -15, 15], rotate: [0, -20, 20, 0], scale: [1.1, 1, 1.1] }}
              transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Card sx={{ p: 3, borderRadius: 4, background: 'linear-gradient(135deg, rgba(227,179,65,0.15) 0%, rgba(76,195,138,0.05) 100%)', border: '1px solid rgba(227,179,65,0.3)', boxShadow: '0 0 30px rgba(227,179,65,0.2)' }}>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={(morphIndex + 2) % morphIcons.length}
                    initial={{ scale: 0.5, opacity: 0, rotate: 45 }}
                    animate={{ scale: 1, opacity: 1, rotate: 0 }}
                    exit={{ scale: 0.5, opacity: 0, rotate: -45 }}
                    transition={{ duration: 0.4 }}
                  >
                    {React.createElement(morphIcons[(morphIndex + 2) % morphIcons.length].icon, {
                      size: 56,
                      color: morphIcons[(morphIndex + 2) % morphIcons.length].color,
                      style: { filter: `drop-shadow(0 0 20px ${morphIcons[(morphIndex + 2) % morphIcons.length].glow})` }
                    })}
                  </motion.div>
                </AnimatePresence>
              </Card>
            </motion.div>
          </Box>

          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <Chip
              icon={<Star size={14} color="#E3B341" fill="#E3B341" />}
              label="AI Shopping-Agent Decision Integrity Layer • Research Prototype"
              variant="outlined"
              sx={{ mb: 3, borderColor: 'primary.main', color: 'primary.light', fontWeight: 700, px: 2.5, py: 1.2, backgroundColor: 'rgba(108,148,255,0.08)', boxShadow: '0 0 20px rgba(108,148,255,0.15)' }}
            />
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.2 }}>
            <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: 900, letterSpacing: '-0.04em', fontSize: { xs: '2.5rem', md: '4.4rem' }, lineHeight: 1.1 }}>
              Trust decisions, <br />
              <Box component="span" sx={{ background: 'linear-gradient(135deg, #6C94FF 0%, #4CC38A 50%, #EC4899 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                not persuasion.
              </Box>
            </Typography>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.4 }}>
            <Typography variant="h6" color="text.secondary" sx={{ maxWidth: '750px', mx: 'auto', mb: 5, lineHeight: 1.6, fontWeight: 400 }}>
              TRUSSTED evaluates AI shopping-agent decisions by extracting product facts, cross-checking independent evidence, ranking options deterministically, testing decision stability, and recording auditable outcomes.
            </Typography>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5, delay: 0.6 }}>
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2.5, flexWrap: 'wrap' }}>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={onNavigateToDashboard}
                  sx={{
                    bgcolor: 'primary.main',
                    fontWeight: 700,
                    px: 4.5,
                    py: 1.8,
                    borderRadius: 3,
                    boxShadow: '0 0 35px rgba(108,148,255,0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    '&:hover': { bgcolor: 'primary.dark' }
                  }}
                >
                  <span>Explore the Dashboard</span>
                  <motion.span
                    animate={{ x: [0, 6, 0] }}
                    transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
                    style={{ display: 'inline-flex', alignItems: 'center' }}
                  >
                    <ArrowRight size={18} />
                  </motion.span>
                </Button>
              </motion.div>
            </Box>
          </motion.div>
        </Container>

        <Container maxWidth="lg" sx={{ my: 6 }}>
          <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.8 }}>
            <Card sx={{
              background: 'linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(30,41,59,0.95) 100%)',
              border: '1px solid',
              borderColor: 'rgba(108,148,255,0.3)',
              borderRadius: 4,
              boxShadow: '0 30px 60px rgba(0,0,0,0.5)',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <Box sx={{ px: 4, py: 2.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Lock size={14} color="#6C94FF" />
                  <Typography variant="caption" sx={{ fontWeight: 800, letterSpacing: '0.1em', color: 'text.secondary' }}>
                    EVIDENCE GRAPH • HOVER A NODE
                  </Typography>
                </Box>
                <Typography variant="caption" sx={{ color: '#4CC38A', fontFamily: 'monospace', fontWeight: 600 }}>
                  {activeNode}
                </Typography>
              </Box>

              <CardContent sx={{ p: 5, minHeight: '280px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
                <Box sx={{ width: '100%', maxWidth: '750px', height: '140px', position: 'relative', display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                  {[
                    { id: 'extraction', label: 'Fact Extraction', color: '#6C94FF', icon: Search, desc: 'Isolating product assertions and agent criteria' },
                    { id: 'crosscheck', label: 'Cross-Check', color: '#4CC38A', icon: Network, desc: 'Verifying claims against independent evidence streams' },
                    { id: 'ranking', label: 'Deterministic Rank', color: '#E3B341', icon: Cpu, desc: 'Scoring options using deterministic multi-factor policy' },
                    { id: 'decision', label: 'Decision Output', color: '#38BDF8', icon: ShieldCheck, desc: 'Issuing verifiable ALLOW, STEP_UP, or BLOCK outcomes' }
                  ].map((node, i) => {
                    const NodeIcon = node.icon;
                    return (
                      <motion.div
                        key={i}
                        whileHover={{ scale: 1.25 }}
                        onHoverStart={() => setActiveNode(node.desc)}
                        onHoverEnd={() => setActiveNode('Hover a node to inspect telemetry')}
                        style={{ cursor: 'pointer', textAlign: 'center', zIndex: 2 }}
                      >
                        <motion.div
                          animate={{ scale: [1, 1.15, 1], boxShadow: [`0 0 10px ${node.color}`, `0 0 25px ${node.color}`, `0 0 10px ${node.color}`] }}
                          transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.4 }}
                          style={{
                            width: 46,
                            height: 46,
                            borderRadius: '50%',
                            backgroundColor: `${node.color}20`,
                            border: `2px solid ${node.color}`,
                            margin: '0 auto 10px auto',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: node.color
                          }}
                        >
                          <NodeIcon size={20} />
                        </motion.div>
                        <Typography variant="caption" sx={{ color: 'text.primary', fontWeight: 700, display: 'block', maxWidth: '130px', fontSize: '11.5px' }}>
                          {node.label}
                        </Typography>
                      </motion.div>
                    );
                  })}
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Container>

        <Container maxWidth="lg" sx={{ my: 12, position: 'relative' }}>

          <Box sx={{ position: 'absolute', top: -70, left: 0, width: '100%', height: '160px', pointerEvents: 'none', display: { xs: 'none', md: 'block' }, zIndex: 5 }}>
            <svg width="100%" height="100%" viewBox="0 0 1100 140" fill="none" xmlns="http://www.w3.org/2000/svg">
              <motion.path
                d="M 80 120 C 300 -40, 700 -40, 1020 90"
                stroke="rgba(108, 148, 255, 0.4)"
                strokeWidth="2.5"
                strokeDasharray="6 6"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
              />

              <motion.circle
                r="6"
                fill="#6C94FF"
                filter="drop-shadow(0 0 10px #6C94FF)"
              >
                <animateMotion
                  dur="4s"
                  repeatCount="indefinite"
                  path="M 80 120 C 300 -40, 700 -40, 1020 90"
                />
              </motion.circle>
            </svg>

            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              style={{ position: 'absolute', top: '15px', left: '28%', fontFamily: 'monospace', fontSize: '11px', color: '#6C94FF', fontWeight: 700 }}
            >
              EXTRACT
            </motion.div>
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              style={{ position: 'absolute', top: '5px', left: '55%', fontFamily: 'monospace', fontSize: '11px', color: '#E3B341', fontWeight: 700 }}
            >
              PERTURB
            </motion.div>
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              style={{ position: 'absolute', top: '35px', left: '72%', fontFamily: 'monospace', fontSize: '11px', color: '#4CC38A', fontWeight: 700 }}
            >
              RECEIPT
            </motion.div>
          </Box>

          <Box sx={{ textAlign: 'center', mb: 8 }}>
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1.5, mb: 1 }}>
              <Star size={20} color="#E3B341" fill="#E3B341" />
              <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.03em' }}>Seven pipeline stages. Complete integrity.</Typography>
              <Star size={20} color="#E3B341" fill="#E3B341" />
            </Box>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>Rigorous zero-trust decision inspection pipeline built for automated shopping agents.</Typography>
          </Box>

          <Grid container spacing={3}>
            {[
              { step: '01', title: 'Extract', desc: 'Isolate key product assertions and agent criteria.', icon: Search, color: '#6C94FF' },
              { step: '02', title: 'Cross-check', desc: 'Verify claims against independent evidence streams.', icon: Network, color: '#38BDF8' },
              { step: '03', title: 'Rank', desc: 'Score options using deterministic multi-factor policy.', icon: Cpu, color: '#A78BFA' },
              { step: '04', title: 'Perturb', desc: 'Test decision stability against input variations.', icon: ShieldAlert, color: '#E3B341' },
              { step: '05', title: 'Decide', desc: 'Issue verifiable ALLOW, STEP_UP, or BLOCK outcomes.', icon: CheckSquare, color: '#4CC38A' },
              { step: '06', title: 'Credential', desc: 'Apply optional authorization proofs.', icon: Sparkles, color: '#EC4899' },
              { step: '07', title: 'Receipt', desc: 'Record auditable outcomes and event trails.', icon: Activity, color: '#6366F1' },
            ].map((card, idx) => {
              const Icon = card.icon;
              return (
                <Grid size={{ xs: 12, sm: 6, md: 4 }} key={idx}>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: idx * 0.1 }}
                    whileHover={{ y: -8, scale: 1.02 }}
                  >
                    <Card sx={{
                      height: '100%',
                      background: 'linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(30,41,59,0.95) 100%)',
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 3.5,
                      p: 2,
                      boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
                      position: 'relative',
                      overflow: 'hidden',
                      '&:hover': { borderColor: card.color }
                    }}>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                          <Typography variant="caption" sx={{ color: card.color, fontWeight: 800, fontFamily: 'monospace', fontSize: '13px' }}>{card.step}</Typography>
                          <Box sx={{ width: 36, height: 36, borderRadius: 2, bgcolor: `${card.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: card.color, border: `1px solid ${card.color}40` }}>
                            <Icon size={18} />
                          </Box>
                        </Box>
                        <Typography variant="h6" sx={{ fontWeight: 800, mb: 1, fontSize: '1.1rem', color: 'text.primary' }}>{card.title}</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '13px', lineHeight: 1.6 }}>{card.desc}</Typography>
                      </CardContent>
                    </Card>
                  </motion.div>
                </Grid>
              );
            })}
          </Grid>
        </Container>

      </Box>
    </motion.div>
  );
};