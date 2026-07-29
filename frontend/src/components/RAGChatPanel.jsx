// frontend/src/components/RAGChatPanel.jsx
import React, { useState } from 'react';
import { API_BASE } from '../utils/constants';

export default function RAGChatPanel() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'System ready. Ask me anything about your vectorized compliance files or telemetry history.', citation: null }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const getHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    };
  };

  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || loading) return;

    const userMessage = inputQuery.trim();
    const updatedMessages = [...messages, { role: 'user', text: userMessage }];
    setInputQuery('');
    setMessages(updatedMessages);
    setLoading(true);

    const token = localStorage.getItem('token');
    const endpoint = token
      ? `${API_BASE}/api/v1/knowledge/agent-query`
      : `${API_BASE}/api/v1/knowledge/query`;

    const chatHistoryPayload = messages.map(msg => ({
      role: msg.role === 'assistant' ? 'assistant' : 'user',
      content: msg.text || ''
    }));

    const body = token
      ? JSON.stringify({ question: userMessage, chat_history: chatHistoryPayload })
      : JSON.stringify({ question: userMessage });

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: getHeaders(),
        body
      });
      
      const data = await response.json();
      
      const textAnswer = data.answer || data.message || 'No response content compiled by vector store.';
      const citationText = data.citations
        ? (Array.isArray(data.citations) ? data.citations.map(c => typeof c === 'string' ? c : c.filename || 'Source').join(', ') : String(data.citations))
        : data.citation || null;

      setMessages((prev) => [
        ...prev, 
        { 
          role: 'assistant', 
          text: textAnswer,
          citation: citationText,
          confidence: data.confidence_score,
          logId: data.log_id,
          rating: null
        }
      ]);
    } catch (error) {
      console.error("RAG Query Failed:", error);
      setMessages((prev) => [
        ...prev, 
        { role: 'assistant', text: '❌ RAG Engine Connection Timeout. Verify backend matrix routing.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (logId, ratingValue, index) => {
    if (!logId) return;
    try {
      await fetch(`${API_BASE}/api/v1/knowledge/feedback`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ log_id: logId, rating: ratingValue }),
      });
      setMessages((prev) => {
        const next = [...prev];
        if (next[index]) {
          next[index] = { ...next[index], rating: ratingValue };
        }
        return next;
      });
    } catch (err) {
      console.error("Feedback error:", err);
    }
  };

  return (
    <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-125">
      {/* Header Panel */}
      <div className="px-6 py-4 border-b border-slate-800/80 bg-slate-900/40 flex items-center space-x-2">
        <span className="text-indigo-400 text-sm animate-pulse">📚</span>
        <div>
          <h3 className="text-xs font-black uppercase tracking-widest text-indigo-300">RAG Vector Explorer</h3>
          <p className="text-[10px] text-slate-500 font-mono">Isolated Database Read Matrix // Non-Mutating Chat Interface</p>
        </div>
      </div>

      {/* Message Output Frame */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-slate-800">
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} space-y-1`}>
            <div className={`max-w-[85%] rounded-xl p-4 text-xs font-mono leading-relaxed shadow-md ${
              msg.role === 'user' 
                ? 'bg-indigo-600 border border-indigo-500/50 text-white' 
                : 'bg-slate-950 border border-slate-900 text-slate-200'
            }`}>
              <p className="whitespace-pre-line">{msg.text}</p>
              
              {/* Conditional Source Citation Render */}
              {msg.citation && (
                <div className="mt-3 pt-2 border-t border-slate-800 text-[10px] text-indigo-400 font-sans flex items-center justify-between space-x-1">
                  <span>📂 Citation: <span className="underline italic text-slate-400 font-mono">{msg.citation}</span></span>
                  {msg.confidence !== undefined && (
                    <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded font-mono text-[9px] font-bold">
                      {msg.confidence}% Confidence
                    </span>
                  )}
                </div>
              )}
            </div>

            {msg.role === 'assistant' && msg.logId && (
              <div className="flex items-center space-x-2 text-[10px] text-slate-500 px-1">
                <span>Rate response:</span>
                <button
                  onClick={() => handleFeedback(msg.logId, 1, i)}
                  className={`px-2 py-0.5 rounded transition-all cursor-pointer font-bold ${
                    msg.rating === 1 ? 'bg-emerald-600 text-white' : 'bg-slate-900 hover:bg-slate-800 text-slate-400'
                  }`}
                >
                  👍 {msg.rating === 1 ? 'Helpful' : 'Yes'}
                </button>
                <button
                  onClick={() => handleFeedback(msg.logId, -1, i)}
                  className={`px-2 py-0.5 rounded transition-all cursor-pointer font-bold ${
                    msg.rating === -1 ? 'bg-rose-600 text-white' : 'bg-slate-900 hover:bg-slate-800 text-slate-400'
                  }`}
                >
                  👎 {msg.rating === -1 ? 'Unhelpful' : 'No'}
                </button>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-950 border border-slate-900 text-slate-500 rounded-xl p-4 text-xs font-mono animate-pulse flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
              <span>Scanning cluster vector spaces...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Form Box */}
      <form onSubmit={handleQuerySubmit} className="p-4 border-t border-slate-800/80 bg-slate-950/60 flex items-center space-x-3">
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask a question about compliance rules, ledger anomalies, or system policies..."
          className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 shadow-inner"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !inputQuery.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white px-5 py-3 rounded-xl text-xs font-extrabold uppercase tracking-wider shadow-lg shadow-indigo-600/10 active:scale-95 transition-all cursor-pointer"
        >
          Query
        </button>
      </form>
    </div>
  );
}