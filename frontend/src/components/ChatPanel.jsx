import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

const API_BASE = 'http://localhost:8000';

export default function ChatPanel({ context }) {
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      text: 'Hello! I\'m your EDI Assistant. Upload a file and I can help explain any errors, segment codes, or HIPAA rules. Ask me anything!',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const question = input.trim();
    if (!question || loading) return;

    const userMsg = { role: 'user', text: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          context: context || null,
        }),
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'ai', text: data.answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          text: `Sorry, I encountered an error: ${err.message}. Please make sure the backend server is running.`,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon">🤖</span>
          AI Assistant
        </div>
        <span className="badge badge-info">Gemini</span>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <div className={`chat-message-avatar ${msg.role}`}>
                {msg.role === 'user' ? '👤' : '✨'}
              </div>
              <div className="chat-message-content">
                <div className="chat-message-name">
                  {msg.role === 'user' ? 'You' : 'EDI Assistant'}
                </div>
                <div className="chat-message-text">
                  {msg.role === 'ai' ? (
                    <ReactMarkdown className="markdown-content">{msg.text}</ReactMarkdown>
                  ) : (
                    msg.text
                  )}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-message ai">
              <div className="chat-message-avatar ai">✨</div>
              <div className="chat-message-content">
                <div className="chat-message-name">EDI Assistant</div>
                <div className="chat-thinking">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Ask about EDI codes, errors, or HIPAA rules..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            id="chat-input"
          />
          <button
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            id="chat-send-btn"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
