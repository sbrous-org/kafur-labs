import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [error, setError] = useState('');
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userQuery = input.trim();
    setInput('');
    setError('');

    setMessages(prev => [...prev, {
      type: 'user',
      content: userQuery,
      timestamp: new Date().toLocaleTimeString()
    }]);

    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/query`, {
        query: userQuery,
        session_id: sessionId
      });

      const { answer, route_taken, sources, confidence } = response.data;

      setMessages(prev => [...prev, {
        type: 'bot',
        content: answer,
        route: route_taken,
        sources: sources,
        confidence: confidence,
        timestamp: new Date().toLocaleTimeString()
      }]);

    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to get response';
      setError(`Error: ${errorMsg}`);
      setMessages(prev => [...prev, {
        type: 'bot',
        content: `Sorry, I encountered an error: ${errorMsg}`,
        error: true,
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError('');
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🗺️ Assam Travel Bot</h1>
        <p>Ask me about places, weather, and travel tips for Assam</p>
      </div>

      <div className="chat-area">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#999', marginTop: '40px' }}>
            <p>👋 Welcome! Ask me about travel in Assam...</p>
            <p style={{ fontSize: '12px', marginTop: '20px' }}>Example queries:</p>
            <ul style={{ listStyle: 'none', fontSize: '13px', marginTop: '10px' }}>
              <li>"Tell me about Kamakhya Temple"</li>
              <li>"What's the weather in Guwahati?"</li>
              <li>"Plan a 2-day trip visiting nature and heritage"</li>
              <li>"Is Pobitora Wildlife Sanctuary worth visiting?"</li>
            </ul>
          </div>
        )}

        {error && (
          <div className="error-message">{error}</div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            <div>
              <div className="message-content">
                {msg.content}
              </div>
              <div className="message-meta">
                {msg.timestamp}
              </div>
              {msg.type === 'bot' && msg.route && (
                <div className="sources">
                  <div>
                    <strong>Route:</strong>
                    <div style={{ marginTop: '4px' }}>
                      {msg.route.split(', ').map((r, i) => (
                        <span key={i} className="route-badge">{r}</span>
                      ))}
                    </div>
                  </div>
                  {msg.sources && Object.keys(msg.sources).length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <strong>Sources:</strong>
                      <div style={{ marginTop: '4px', fontSize: '11px' }}>
                        {msg.sources.kb_results && (
                          <div>📍 KB: {msg.sources.kb_results.map(r => r.site_name).join(', ')}</div>
                        )}
                        {msg.sources.weather_location && (
                          <div>🌤️ Weather: {msg.sources.weather_location}</div>
                        )}
                      </div>
                    </div>
                  )}
                  <div style={{ marginTop: '6px', fontSize: '10px' }}>
                    Confidence: {(msg.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message bot">
            <div className="loading">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <div className="input-area">
        <form onSubmit={sendMessage} style={{ display: 'flex', gap: '10px', width: '100%' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about places, weather, travel plans..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            {loading ? 'Sending...' : 'Send'}
          </button>
        </form>
        {messages.length > 0 && (
          <button className="clear-btn" onClick={clearChat}>Clear</button>
        )}
      </div>
    </div>
  );
}

export default App;
