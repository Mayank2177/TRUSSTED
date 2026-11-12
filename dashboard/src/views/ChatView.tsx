import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  TextField,
  Button,
  Chip,
  IconButton,
  Tooltip,
  useTheme,
} from '@mui/material';
import {
  Sparkles,
  Send,
  Bot,
  User,
  Plus,
  Trash2,
  RefreshCw,
  Laptop,
  Smartphone,
  ShieldAlert,
  HelpCircle,
} from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';

interface Message {
  sender: 'user' | 'bot';
  text: string;
  isDemo?: boolean;
}

export const ChatView: React.FC = () => {
  const theme = useTheme();
  const prefersReducedMotion = useReducedMotion();
  const isDark = theme.palette.mode === 'dark';

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const suggestions = [
    { title: 'Find a laptop for programming under ₹60,000.', icon: Laptop },
    { title: 'Compare two smartphones based on specifications.', icon: Smartphone },
    { title: 'Evaluate a product listing for misleading claims.', icon: ShieldAlert },
    { title: 'Explain why a shopping-agent recommendation was blocked.', icon: HelpCircle },
  ];

  const getDemoResponse = (query: string): string => {
    const q = query.toLowerCase();
    if (q.includes('laptop') || q.includes('60,000') || q.includes('programming')) {
      return 'Demo response: Live product catalog and real-time inventory pricing are not connected yet. Once connected, TRUSSTED will evaluate laptop specifications against verified merchant feeds.';
    }
    if (q.includes('smartphone') || q.includes('phone') || q.includes('compare')) {
      return 'Demo response: Live product comparison feeds are not connected yet. This demo interface simulates assistant interactions without external API data.';
    }
    if (q.includes('misleading') || q.includes('claim') || q.includes('evaluate')) {
      return 'Demo response: Live evidence cross-checking is not connected yet. In production, TRUSSTED verifies merchant listing claims against independent registry feeds.';
    }
    if (q.includes('block') || q.includes('recommendation')) {
      return 'Demo response: Live decision trace logs are not connected yet. Blocked recommendations generate signed cryptographic receipts once the backend evaluation engine is active.';
    }
    return `Demo response: Received query "${query.trim()}". Live product research, external verification, and AI backend capabilities are not connected in this frontend prototype.`;
  };

  const handleSend = (textToSend?: string) => {
    const query = textToSend !== undefined ? textToSend : input;
    if (!query || !query.trim()) return;

    const userMsg: Message = { sender: 'user', text: query.trim() };
    setMessages((prev) => [...prev, userMsg]);
    if (textToSend === undefined) setInput('');
    setIsLoading(true);

    // Simulated demo response delay
    setTimeout(() => {
      setIsLoading(false);
      const botMsg: Message = {
        sender: 'bot',
        text: getDemoResponse(query),
        isDemo: true,
      };
      setMessages((prev) => [...prev, botMsg]);
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setInput('');
  };

  const handleClear = () => {
    if (messages.length === 0) return;
    if (window.confirm('Are you sure you want to clear the current conversation?')) {
      setMessages([]);
    }
  };

  return (
    <motion.div
      initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100vh - 130px)',
          maxWidth: '1000px',
          mx: 'auto',
          position: 'relative',
        }}
      >
        {/* Header & Controls */}
        <Box
          sx={{
            mb: 2.5,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 2,
          }}
        >
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: '-0.03em', mb: 0.5 }}>
              Shop with AI
            </Typography>
            <Typography variant="body2" color="text.secondary">
              An intelligent shopping assistant that evaluates product information and helps make more transparent, evidence-based decisions.
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<Plus size={16} />}
              onClick={handleNewConversation}
              sx={{ fontWeight: 700, borderRadius: 2, borderColor: 'divider', color: 'text.primary' }}
            >
              New Chat
            </Button>
            <Tooltip title="Clear Conversation">
              <IconButton
                size="small"
                onClick={handleClear}
                sx={{ border: '1px solid', borderColor: 'divider', color: 'text.secondary', borderRadius: 2 }}
              >
                <Trash2 size={16} />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Chat Main Area */}
        <Card
          sx={{
            flexGrow: 1,
            mb: 2,
            display: 'flex',
            flexDirection: 'column',
            bgcolor: 'background.paper',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 4,
            overflow: 'hidden',
            boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
          }}
        >
          {/* Scrollable Message History Area with custom clean scrollbar */}
          <Box
            sx={{
              flexGrow: 1,
              p: { xs: 2, md: 3 },
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 2.5,
              scrollbarWidth: 'thin',
              scrollbarColor: isDark ? '#30363D transparent' : '#D0D7DE transparent',
              '&::-webkit-scrollbar': {
                width: '6px',
              },
              '&::-webkit-scrollbar-track': {
                background: 'transparent',
              },
              '&::-webkit-scrollbar-thumb': {
                backgroundColor: isDark ? '#30363D' : '#D0D7DE',
                borderRadius: '3px',
              },
            }}
          >
            {messages.length === 0 ? (
              /* Welcome Hero & Suggestion Cards */
              <Box
                sx={{
                  my: 'auto',
                  py: 4,
                  textAlign: 'center',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Box
                  sx={{
                    width: 52,
                    height: 52,
                    borderRadius: 3,
                    background: 'linear-gradient(135deg, #6C94FF 0%, #4F46E5 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    mb: 2.5,
                    boxShadow: '0 0 25px rgba(108,148,255,0.3)',
                  }}
                >
                  <Sparkles size={26} color="#FFF" />
                </Box>

                <Typography variant="h5" sx={{ fontWeight: 800, mb: 1, letterSpacing: '-0.02em' }}>
                  What are you looking for today?
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ maxWidth: '500px', mb: 4 }}>
                  Describe a product, compare options, or ask TRUSSTED to evaluate a shopping recommendation.
                </Typography>

                
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' },
                    gap: 2,
                    width: '100%',
                    maxWidth: '750px',
                    textAlign: 'left',
                  }}
                >
                  {suggestions.map((item, idx) => {
                    const Icon = item.icon;
                    return (
                      <Card
                        key={idx}
                        variant="outlined"
                        onClick={() => setInput(item.title)}
                        sx={{
                          p: 2.5,
                          borderRadius: 3,
                          cursor: 'pointer',
                          bgcolor: 'background.default',
                          borderColor: 'divider',
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            borderColor: 'primary.main',
                            bgcolor: isDark ? 'rgba(108,148,255,0.04)' : 'rgba(36,87,214,0.02)',
                            transform: prefersReducedMotion ? 'none' : 'translateY(-2px)',
                          },
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                          <Box
                            sx={{
                              p: 1,
                              borderRadius: 2,
                              bgcolor: 'rgba(108,148,255,0.1)',
                              color: 'primary.main',
                              flexShrink: 0,
                            }}
                          >
                            <Icon size={18} />
                          </Box>
                          <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary', lineHeight: 1.4 }}>
                            {item.title}
                          </Typography>
                        </Box>
                      </Card>
                    );
                  })}
                </Box>
              </Box>
            ) : (

              messages.map((msg, idx) => (
                <Box
                  key={idx}
                  sx={{
                    display: 'flex',
                    gap: 2,
                    alignItems: 'flex-start',
                    alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: { xs: '90%', md: '75%' },
                  }}
                >
                  {msg.sender === 'bot' && (
                    <Box
                      sx={{
                        width: 34,
                        height: 34,
                        borderRadius: 2,
                        bgcolor: 'rgba(108,148,255,0.15)',
                        color: '#6C94FF',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        border: '1px solid rgba(108,148,255,0.3)',
                      }}
                    >
                      <Bot size={18} />
                    </Box>
                  )}
                  <Box
                    sx={{
                      p: 2.5,
                      borderRadius: 3,
                      bgcolor: msg.sender === 'user' ? 'primary.main' : 'background.default',
                      color: msg.sender === 'user' ? '#fff' : 'text.primary',
                      border: '1px solid',
                      borderColor: msg.sender === 'user' ? 'primary.main' : 'divider',
                      boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                    }}
                  >
                    {msg.isDemo && (
                      <Chip
                        label="Demo response — AI backend not connected"
                        size="small"
                        sx={{
                          mb: 1.5,
                          height: 22,
                          fontSize: '10.5px',
                          fontFamily: 'monospace',
                          bgcolor: 'rgba(227,179,65,0.15)',
                          color: '#E3B341',
                          fontWeight: 700,
                        }}
                      />
                    )}
                    <Typography variant="body2" sx={{ lineHeight: 1.6, fontWeight: 500, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {msg.text}
                    </Typography>
                  </Box>
                  {msg.sender === 'user' && (
                    <Box
                      sx={{
                        width: 34,
                        height: 34,
                        borderRadius: 2,
                        bgcolor: 'rgba(76,195,138,0.15)',
                        color: '#4CC38A',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        border: '1px solid rgba(76,195,138,0.3)',
                      }}
                    >
                      <User size={18} />
                    </Box>
                  )}
                </Box>
              ))
            )}

            {isLoading && (
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', alignSelf: 'flex-start' }}>
                <Box
                  sx={{
                    width: 34,
                    height: 34,
                    borderRadius: 2,
                    bgcolor: 'rgba(108,148,255,0.15)',
                    color: '#6C94FF',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    border: '1px solid rgba(108,148,255,0.3)',
                  }}
                >
                  <Bot size={18} />
                </Box>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 3,
                    bgcolor: 'background.default',
                    border: '1px solid',
                    borderColor: 'divider',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                  }}
                >
                  <RefreshCw className="animate-spin" size={16} color="#6C94FF" />
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                    Simulating demo response...
                  </Typography>
                </Box>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Box>

          <Box
            component="form"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            sx={{
              p: 2,
              borderTop: '1px solid',
              borderColor: 'divider',
              bgcolor: 'background.default',
              display: 'flex',
              gap: 1.5,
              alignItems: 'center',
            }}
          >
            <TextField
              fullWidth
              multiline
              maxRows={4}
              size="small"
              placeholder="Ask the shopping agent for product recommendations... (Press Enter to send, Shift+Enter for new line)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2.5,
                  py: 1,
                },
              }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={isLoading || !input.trim()}
              sx={{
                px: 3,
                py: 1.2,
                borderRadius: 2.5,
                bgcolor: '#6C94FF',
                fontWeight: 700,
                flexShrink: 0,
                '&:hover': { bgcolor: '#5275e0' },
              }}
              endIcon={<Send size={16} />}
            >
              Send
            </Button>
          </Box>
        </Card>
      </Box>
    </motion.div>
  );
};

export default ChatView;