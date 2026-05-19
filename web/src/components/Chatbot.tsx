import React, { useState, useRef, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  source?: string;
  isError?: boolean;
}

import { useLanguage } from "../state/LanguageContext";
import { t } from "../i18n";

const SUGGESTED_DEFAULT = {
  en: [
    'Which crops are best for this season?',
    'What does the ERI score mean?',
    'How is irrigation strategy calculated?',
    'Explain the SHAP values shown',
    'What are the climate risk levels?',
    'Which cities have the highest crop viability?',
  ],
  hi: [
    'इस मौसम के लिए कौन सी फसलें बेहतर हैं?',
    'ERI स्कोर का क्या मतलब है?',
    'सिंचाई रणनीति कैसे निकाली जाती है?',
    'दिखाए गए SHAP मान समझाएं',
    'जलवायु जोखिम स्तर क्या हैं?',
    'किन शहरों में फसल व्यवहार्यता सबसे अधिक है?',
  ],
  kn: [
    'ಈ ಋತುವಿಗೆ ಯಾವ ಬೆಳೆಗಳು ಉತ್ತಮ?',
    'ERI ಅಂಕದ ಅರ್ಥವೇನು?',
    'ನೀರಾವರಿ ತಂತ್ರವನ್ನು ಹೇಗೆ ಲೆಕ್ಕ ಹಾಕುತ್ತಾರೆ?',
    'ತೋರಿಸಿರುವ SHAP ಮೌಲ್ಯಗಳನ್ನು ವಿವರಿಸಿ',
    'ಹವಾಮಾನ ಅಪಾಯ ಮಟ್ಟಗಳು ಯಾವುವು?',
    'ಯಾವ ನಗರಗಳಲ್ಲಿ ಬೆಳೆ ಸಾಧ್ಯತೆ ಹೆಚ್ಚು?',
  ],
} as const;

function formatBotText(text: string): React.ReactNode {
  const lines = text.split(/\n+/);
  return lines.map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return null;
    // Bullet points
    if (/^[-•*]\s/.test(trimmed)) {
      return (
        <li key={i} className="chat-bullet">
          {renderInline(trimmed.replace(/^[-•*]\s/, ''))}
        </li>
      );
    }
    return (
      <p key={i} className="chat-para">
        {renderInline(trimmed)}
      </p>
    );
  }).filter(Boolean);
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function SourceBadge({ source }: { source: string }) {
  const { lang } = useLanguage();
  const labels: Record<string, string> = {
    'docs/explanation.md': 'Explanation',
    'docs/LAYMAN_GUIDE.md': 'Guide',
    'docs/MENTOR_SUMMARY.md': 'Summary',
    'docs/READING_ROADMAP.md': 'Roadmap',
    'docs/instructions.md': 'Instructions',
    'docs/data_flow.md': 'Data Flow',
    'output/baseline_metrics.json': 'Metrics',
    'output/crop_advisory.json': 'Advisory',
    'output/crop_viability_events.json': 'Viability',
    'output/exploitation_risk_report.json': 'Risk Report',
    'output/irrigation_strategy.json': 'Irrigation',
    'output/shap_explanation.json': 'SHAP',
    'output/transition_report.json': 'Transition',
    'output/viability_trend_report.json': 'Trends',
  };
  const parts = source.split(', ').slice(0, 2);
  return (
    <div className="chat-sources">
      <span className="chat-sources-label">{t(lang, "chat.source")}</span>
      {parts.map((s) => (
        <span key={s} className="chat-source-tag">
          {labels[s] ?? s}
        </span>
      ))}
    </div>
  );
}

const Chatbot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [isOpen]);

  const { lang } = useLanguage();

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isLoading) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      text: message.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);
    setShowSuggestions(false);

    // Build history payload — last 8 messages for context
    const historySnapshot = [...messages, userMsg].slice(-8).map(m => ({
      id: m.id,
      text: m.text,
      isUser: m.isUser,
    }));

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message.trim(), history: historySnapshot }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();

      setMessages(prev => [...prev, {
        id: `b-${Date.now()}`,
        text: data.response,
        isUser: false,
        timestamp: new Date(),
        source: data.source && data.source !== 'system' ? data.source : undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        text: t(lang, "chat.connection_failed"),
        isUser: false,
        timestamp: new Date(),
        isError: true,
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, lang, messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setShowSuggestions(true);
    inputRef.current?.focus();
  };

  const isEmpty = messages.length === 0;

  return (
    <>
      <button
        className={`chatbot-toggle ${isOpen ? 'chatbot-toggle--open' : ''}`}
        onClick={() => setIsOpen(v => !v)}
        aria-label={isOpen ? t(lang, "chat.close") : t(lang, "chat.open")}
        title={isOpen ? t(lang, "chat.close") : t(lang, "chat.ask")}
      >
        <span className="chatbot-toggle-icon">
          {isOpen ? (
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <line x1="5" y1="5" x2="15" y2="15" /><line x1="15" y1="5" x2="5" y2="15" />
            </svg>
          ) : (
            <svg viewBox="0 0 22 22" fill="none">
              <path d="M3 6.5C3 5.12 4.12 4 5.5 4h11C17.88 4 19 5.12 19 6.5v7C19 14.88 17.88 16 16.5 16H13l-3 3-3-3H5.5C4.12 19 3 17.88 3 16.5v-10z"
                fill="rgba(255,255,255,0.25)" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
              <circle cx="8" cy="10" r="1.1" fill="white"/>
              <circle cx="11" cy="10" r="1.1" fill="white"/>
              <circle cx="14" cy="10" r="1.1" fill="white"/>
            </svg>
          )}
        </span>
        {!isOpen && <span className="chatbot-toggle-pulse" />}
      </button>

      <div className={`chatbot-window ${isOpen ? 'chatbot-window--visible' : ''}`} aria-hidden={!isOpen}>
        {/* Header */}
        <div className="chatbot-header">
          <div className="chatbot-header-info">
            <div className="chatbot-avatar">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M12 3C8.5 3 6 5.5 6 9c0 2 .8 3.8 2.1 5L7 17h10l-1.1-3C17.2 12.8 18 11 18 9c0-3.5-2.5-6-6-6z"
                  fill="rgba(255,255,255,0.3)" stroke="rgba(255,255,255,0.8)" strokeWidth="1.4"/>
                <path d="M9 17v1a3 3 0 006 0v-1" stroke="rgba(255,255,255,0.7)" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
            </div>
            <div>
              <div className="chatbot-header-title">{t(lang, "chat.title")}</div>
              <div className="chatbot-header-sub">{t(lang, 'chat.subtitle')}</div>
            </div>
          </div>
          <div className="chatbot-header-actions">
            {messages.length > 0 && (
              <button className="chatbot-action-btn" onClick={clearConversation} title={t(lang, "chat.clear")} aria-label={t(lang, "chat.clear")}>
                <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                  <path d="M3 4h12M7 4V3h4v1M5 4l1 11h6l1-11"/>
                </svg>
              </button>
            )}
            <button className="chatbot-action-btn" onClick={() => setIsOpen(false)} aria-label={t(lang, "chat.close")}>
              <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="4" y1="4" x2="14" y2="14"/><line x1="14" y1="4" x2="4" y2="14"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="chatbot-messages">
          {isEmpty && (
            <div className="chatbot-welcome">
              <div className="chatbot-welcome-icon">🌾</div>
                  <h4>{t(lang, 'chat.title')}</h4>
                  <p>{t(lang, 'chat.subtitle')}</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`chat-message chat-message--${msg.isUser ? 'user' : 'bot'} ${msg.isError ? 'chat-message--error' : ''}`}>
              {!msg.isUser && (
                <div className="chat-bot-dot" aria-hidden="true" />
              )}
              <div className="chat-bubble">
                {msg.isUser ? (
                  <span>{msg.text}</span>
                ) : (
                  <div className="chat-formatted">
                    {formatBotText(msg.text)}
                  </div>
                )}
                <div className="chat-meta">
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
              {!msg.isUser && msg.source && <SourceBadge source={msg.source} />}
            </div>
          ))}

          {isLoading && (
            <div className="chat-message chat-message--bot">
              <div className="chat-bot-dot" aria-hidden="true" />
              <div className="chat-bubble chat-bubble--typing">
                <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {showSuggestions && isEmpty && (
          <div className="chatbot-suggestions">
            {SUGGESTED_DEFAULT[lang].map((q) => (
              <button key={q} className="suggestion-chip" onClick={() => sendMessage(q)}>
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <form className="chatbot-input-row" onSubmit={handleSubmit}>
          <div className="chatbot-input-wrap">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t(lang, 'chat.placeholder')}
              disabled={isLoading}
              maxLength={400}
              aria-label={t(lang, "chat.placeholder")}
            />
            {inputValue.length > 300 && (
              <span className="char-count">{400 - inputValue.length}</span>
            )}
          </div>
          <button
            type="submit"
            className="chatbot-send-btn"
            disabled={isLoading || !inputValue.trim()}
            aria-label={t(lang, "chat.send")}
          >
            {isLoading ? (
              <svg viewBox="0 0 20 20" fill="none" className="spin">
                <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="2.5" strokeDasharray="22 22" strokeLinecap="round"/>
              </svg>
            ) : (
              <svg viewBox="0 0 20 20" fill="none">
                <path d="M3 10L17 10M11 4l6 6-6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>
        </form>
      </div>
    </>
  );
};

export default Chatbot;
