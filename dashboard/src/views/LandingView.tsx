import React, { useState } from 'react';
import { Box, Button, Container, Grid, Typography, Card, CardContent, Chip } from '@mui/material';
import { ArrowRight, Cpu, Sparkles, Network, Search, CheckSquare, ShieldAlert } from 'lucide-react';
import { motion } from 'framer-motion';

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

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', color: 'text.primary', pb: 12, overflowX: 'hidden', position: 'relative' }}>

        {/* --- TOP RIGHT AUTH ACTIONS BAR --- */}
        <motion.div
          initial={{ opacity: 0, y: -15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          style={{ position: 'absolute', top: 24, right: 32, zIndex: 10, display: 'flex', gap: '12px' }}
        >
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={onNavigateToLogin}
              sx={{ borderColor: 'divider', color: 'text.primary', fontWeight: 600, px: 2.5, py: 1, borderRadius: 2, '&:hover': { bgcolor: 'action.hover' } }}
            >
              Sign In
            </Button>
          </motion.div>
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              variant="contained"
              size="small"
              onClick={onNavigateToSignup}
              sx={{ bgcolor: 'primary.main', fontWeight: 600, px: 2.5, py: 1, borderRadius: 2, '&:hover': { bgcolor: 'primary.dark' } }}
            >
              Sign Up
            </Button>
          </motion.div>
        </motion.div>

        {/* --- HERO SECTION --- */}
        <Container maxWidth="lg" sx={{ pt: 14, pb: 6, textAlign: 'center' }}>
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <Chip
              icon={<Sparkles size={14} color="#818CF8" />}
              label="Decision Integrity Engine • Research Prototype"
              variant="outlined"
              sx={{ mb: 3, borderColor: 'primary.main', color: 'primary.light', fontWeight: 700, px: 2, py: 1, backgroundColor: 'action.hover' }}
            />
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.2 }}>
            <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: 900, letterSpacing: '-0.04em', fontSize: { xs: '2.5rem', md: '4.2rem' }, lineHeight: 1.1 }}>
              Verify before <br />
              <Box component="span" sx={{ background: 'linear-gradient(135deg, #6366F1 0%, #3B82F6 50%, #EC4899 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                you trust.
              </Box>
            </Typography>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.4 }}>
            <Typography variant="h6" color="text.secondary" sx={{ maxWidth: '750px', mx: 'auto', mb: 5, lineHeight: 1.6, fontWeight: 400 }}>
              Behind every checkout link is a story[cite: 6]. TRUSSTED connects the signals—DNS telemetry, certificates, and merchant intent—so you can spot phishing storefronts instantly.
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
                    px: 4,
                    py: 1.5,
                    borderRadius: 2.5,
                    boxShadow: '0 0 30px rgba(99,102,241,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    '&:hover': { bgcolor: 'primary.dark' }
                  }}
                >
                  <span>Launch Live Dashboard</span>
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

        {/* --- LIVE EVIDENCE GRAPH HERO COMPONENT --- */}
        <Container maxWidth="lg" sx={{ my: 6 }}>
          <motion.div initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.8 }}>
            <Card sx={{
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 4,
              boxShadow: '0 30px 60px rgba(0,0,0,0.4)',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <Box sx={{ px: 4, py: 2.5, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="caption" sx={{ fontWeight: 800, letterSpacing: '0.1em', color: 'text.secondary' }}>
                  LIVE EVIDENCE GRAPH • HOVER A NODE
                </Typography>
                <Typography variant="caption" sx={{ color: 'primary.main', fontFamily: 'monospace' }}>
                  {activeNode}
                </Typography>
              </Box>

              <CardContent sx={{ p: 5, minHeight: '280px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
                <Box sx={{ width: '100%', maxWidth: '700px', height: '140px', position: 'relative', display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                  {[
                    { id: 'paypal-secure-login.com', label: 'paypal-secure-login.com', color: '#EF4444', desc: 'Phishing domain detected via OpenPhish' },
                    { id: 'TLS 1.3 valid', label: 'TLS 1.3 Valid', color: '#10B981', desc: 'Certificate issuer: Let’s Encrypt (Dynamic CA)' },
                    { id: 'RDAG 3 days old', label: 'RDAP: 3 Days Old', color: '#F59E0B', desc: 'Domain registered 72 hours ago' },
                    { id: 'High Risk', label: 'High Risk Score (87%)', color: '#EF4444', desc: 'Triggered Scenario S1 Phishing Storefront' }
                  ].map((node, i) => (
                    <motion.div
                      key={i}
                      whileHover={{ scale: 1.25 }}
                      onHoverStart={() => setActiveNode(node.desc)}
                      onHoverEnd={() => setActiveNode('Hover a node to inspect telemetry')}
                      style={{ cursor: 'pointer', textAlign: 'center', zIndex: 2 }}
                    >
                      <motion.div
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
                        style={{ width: 14, height: 14, borderRadius: '50%', backgroundColor: node.color, margin: '0 auto 8px auto', boxShadow: `0 0 15px ${node.color}` }}
                      />
                      <Typography variant="caption" sx={{ color: 'text.primary', fontWeight: 600, display: 'block', maxWidth: '120px', fontSize: '11px' }}>
                        {node.label}
                      </Typography>
                    </motion.div>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Container>

        {/* --- FIVE STEPS BENTO GRID WITH ANIMATED TRAJECTORY ARC OVERLAY --- */}
        <Container maxWidth="lg" sx={{ my: 10, position: 'relative' }}>

          {/* Animated SVG Curved Trajectory Arc with Floating Hex Labels (Matching reference screenshot) */}
          <Box sx={{ position: 'absolute', top: -60, left: 0, width: '100%', height: '160px', pointerEvents: 'none', display: { xs: 'none', md: 'block' }, zIndex: 5 }}>
            <svg width="100%" height="100%" viewBox="0 0 1100 140" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Glowing Curved Background Path */}
              <motion.path
                d="M 80 120 C 300 -40, 700 -40, 1020 90"
                stroke="rgba(99, 102, 241, 0.35)"
                strokeWidth="2"
                strokeDasharray="6 6"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
              />

              {/* Traveling Pulse Head */}
              <motion.circle
                r="5"
                fill="#6366F1"
                filter="drop-shadow(0 0 8px #6366F1)"
              >
                <animateMotion
                  dur="4s"
                  repeatCount="indefinite"
                  path="M 80 120 C 300 -40, 700 -40, 1020 90"
                />
              </motion.circle>
            </svg>

            {/* Floating Hex Telemetry Nodes along the Arc */}
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              style={{ position: 'absolute', top: '15px', left: '28%', fontFamily: 'monospace', fontSize: '10px', color: '#818CF8', opacity: 0.8 }}
            >
              38
            </motion.div>
            <motion.div
              animate={{ y: [0, 6, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              style={{ position: 'absolute', top: '5px', left: '55%', fontFamily: 'monospace', fontSize: '10px', color: '#3B82F6', opacity: 0.8 }}
            >
              94
            </motion.div>
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              style={{ position: 'absolute', top: '35px', left: '72%', fontFamily: 'monospace', fontSize: '10px', color: '#10B981', opacity: 0.8 }}
            >
              89
            </motion.div>
          </Box>

          <Box sx={{ textAlign: 'center', mb: 6 }}>
            <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.03em' }}>Five steps. One answer[cite: 7].</Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>Rigorous zero-trust inspection pipeline built for automated checkout protocols.</Typography>
          </Box>

          <Grid container spacing={3}>
            {[
              { step: '01', title: 'Submit', desc: 'A link, domain, or transaction payload[cite: 7].', icon: Search },
              { step: '02', title: 'Investigate', desc: 'DNS, redirects, SSL certificates, threat feeds[cite: 7].', icon: Network },
              { step: '03', title: 'Analyse', desc: 'Rules find it. AI explains it[cite: 7].', icon: Cpu },
              { step: '04', title: 'Assess', desc: 'One of five clear risk levels[cite: 7].', icon: ShieldAlert },
              { step: '05', title: 'Verify', desc: 'A record no one can alter[cite: 7].', icon: CheckSquare },
            ].map((card, idx) => {
              const Icon = card.icon;
              return (
                <Grid item xs={12} sm={6} md={2.4} key={idx}>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: idx * 0.1 }}
                    whileHover={{ y: -8, scale: 1.02 }}
                  >
                    <Card sx={{ height: '100%', bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 3, p: 1 }}>
                      <CardContent>
                        <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 800, fontFamily: 'monospace' }}>{card.step}</Typography>
                        <Box sx={{ my: 2, color: 'primary.main' }}><Icon size={24} /></Box>
                        <Typography variant="h6" sx={{ fontWeight: 800, mb: 1, fontSize: '1.05rem' }}>{card.title}</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '12.5px', lineHeight: 1.5 }}>{card.desc}</Typography>
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