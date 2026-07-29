// frontend/src/views/KnowledgeHubView.jsx
import React, { useState, useEffect, useRef } from 'react';
import { API_BASE } from '../utils/constants';

function KnowledgeHubView({ onIngestionRefresh }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const fileInputRef = useRef(null);

  const getHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchRegisteredFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/files`, { headers: getHeaders() });
      const data = await res.json();
      const rawFiles = Array.isArray(data) ? data : (data.files || data.data || []);
      setFiles(rawFiles);
    } catch (err) {
      console.error('Error fetching file repository list:', err);
    }
  };

  useEffect(() => {
    fetchRegisteredFiles();
  }, []);

  const handleFileUpload = async (e) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;

    setUploading(true);
    for (let i = 0; i < selectedFiles.length; i++) {
      const formData = new FormData();
      formData.append('files', selectedFiles[i]);

      try {
        const res = await fetch(`${API_BASE}/api/v1/knowledge/upload`, {
          method: 'POST',
          headers: getHeaders(),
          body: formData,
        });
        const result = await res.json();

        // Handle async 202 status polling
        if (res.status === 202 || result.status === 'processing') {
          const jobId = result.job_id || (result.results && result.results[0] && result.results[0].job_id);
          if (jobId) {
            let completed = false;
            let attempts = 0;
            while (!completed && attempts < 30) {
              await new Promise((r) => setTimeout(r, 1500));
              attempts++;
              const statusRes = await fetch(`${API_BASE}/api/v1/knowledge/ingest-status/${jobId}`, { headers: getHeaders() });
              if (statusRes.ok) {
                const statusData = await statusRes.json();
                if (statusData.status === 'completed' || statusData.status === 'failed') {
                  completed = true;
                }
              }
            }
          }
        }
      } catch (err) {
        console.error('Network failure uploading file node:', err);
      }
    }
    setUploading(false);
    await fetchRegisteredFiles();
    if (onIngestionRefresh) onIngestionRefresh(); // Refreshes parent feeds
  };

  const handleAskRAGCore = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || queryLoading) return;

    const userMessage = chatInput.trim();
    const updatedMessages = [...chatMessages, { sender: 'user', text: userMessage }];
    setChatMessages(updatedMessages);
    setChatInput('');
    setQueryLoading(true);

    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json', ...getHeaders() };

    const chatHistoryPayload = chatMessages.map((msg) => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      content: msg.text || '',
    }));

    const endpoint = token ? `${API_BASE}/api/v1/knowledge/agent-query` : `${API_BASE}/api/v1/knowledge/query`;
    const body = token
      ? JSON.stringify({ question: userMessage, chat_history: chatHistoryPayload })
      : JSON.stringify({ question: userMessage });

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers,
        body,
      });
      const data = await res.json();

      const textAnswer = data.answer || data.message || 'No response content compiled.';
      const citationText = data.citations
        ? Array.isArray(data.citations)
          ? data.citations.map((c) => (typeof c === 'string' ? c : c.filename || 'Source')).join(', ')
          : String(data.citations)
        : data.citation || null;

      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'system',
          text: textAnswer,
          citation: citationText,
          confidence: data.confidence_score,
          logId: data.log_id,
          resolvedQuery: data.resolved_query,
          rating: null,
        },
      ]);
    } catch (err) {
      console.error('RAG search matrix failure:', err);
      setChatMessages((prev) => [
        ...prev,
        { sender: 'system', text: '⚠️ Connection timeout. Unable to process context vectors.' },
      ]);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleFeedback = async (logId, ratingValue, index) => {
    if (!logId) return;
    try {
      await fetch(`${API_BASE}/api/v1/knowledge/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getHeaders() },
        body: JSON.stringify({ log_id: logId, rating: ratingValue }),
      });
      setChatMessages((prev) => {
        const next = [...prev];
        if (next[index]) {
          next[index] = { ...next[index], rating: ratingValue };
        }
        return next;
      });
    } catch (err) {
      console.error('Feedback submission error:', err);
    }
  };


  return (
    <div className="space-y-8 animate-fade-in">
      {/* Structural Headers */}
      <div>
        <h2 className="text-base font-black tracking-wider text-white uppercase">EMKA Knowledge Hub Repository</h2>
        <p className="text-xs text-slate-400 mt-1">
          Vectorized corporate storage core. Upload records to slice them into live persistent data arrays.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column: Multi-Format Upload Zone & Listing */}
        <div className="space-y-6 lg:col-span-1">
          <div 
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-800 hover:border-indigo-500/60 bg-slate-900/20 rounded-2xl p-6 text-center transition-all duration-200 cursor-pointer group shadow-inner"
          >
            <input 
              type="file" 
              ref={fileInputRef}
              onChange={handleFileUpload}
              multiple
              accept=".txt,.csv,.pdf,.docx,.xlsx" 
              className="hidden" 
            />
            <div className="text-3xl mb-2 group-hover:scale-110 transition-transform">📂</div>
            <p className="text-xs font-bold text-slate-200 group-hover:text-indigo-400 transition-colors uppercase tracking-wider">
              {uploading ? 'Vectorizing Core Nodes...' : 'Ingest Document Matrix'}
            </p>
            <p className="text-[10px] text-slate-500 mt-2 font-medium leading-relaxed">
              Supported layouts:<br />
              <strong className="text-slate-400">.pdf, .docx, .xlsx, .csv, .txt</strong>
            </p>
          </div>

          {/* Persistent File Grid Registry */}
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-5 space-y-4 shadow-2xl">
            <h3 className="text-xs font-black text-slate-400 tracking-widest uppercase">Active Collections</h3>
            {files.length === 0 ? (
              <p className="text-[11px] text-slate-600 font-mono py-4 text-center">NO REGISTERED WORKSPACE NODES FOUND</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {files.map((file) => (
                  <div key={file.id} className="flex items-center justify-between p-3 bg-slate-900/40 rounded-xl border border-slate-800/40 text-xs">
                    <span className="font-mono text-slate-300 truncate max-w-37.5" title={file.filename || file.file_name}>
                      📄 {file.filename || file.file_name || 'Unknown'}
                    </span>
                    <span className="text-[9px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-lg font-bold">
                      {file.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: High-Availability Conversational RAG Panel */}
        <div className="lg:col-span-2 bg-slate-950/40 border border-slate-800/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-130">
          <div className="p-4 bg-slate-900/40 border-b border-slate-800/80 flex items-center justify-between">
            <h3 className="text-xs font-black text-slate-200 tracking-wider uppercase flex items-center space-x-2">
              <span className="inline-block h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
              <span>Cognitive Knowledge Synthesis Core</span>
            </h3>
          </div>

          {/* Interactive Chat Board Streams */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4 font-mono text-xs">
            {chatMessages.length === 0 && (
              <div className="text-center py-24 text-slate-600 tracking-wide">
                SYSTEM STANDBY // Input search vectors to query indexed workspace knowledge clusters.
              </div>
            )}
            
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} space-y-1.5`}>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 px-1">
                  {msg.sender === 'user' ? '// Operations User' : '// EMKA Assistant'}
                </span>
                <div className={`p-4 rounded-xl border max-w-[85%] leading-relaxed whitespace-pre-line ${
                  msg.sender === 'user' 
                    ? 'bg-indigo-600/10 border-indigo-500/30 text-indigo-200' 
                    : 'bg-slate-950/90 border-slate-800 text-slate-300 shadow-inner'
                }`}>
                  {msg.text}
                </div>

                {msg.citation && (
                  <div className="text-[10px] text-indigo-400 bg-indigo-500/5 border border-indigo-500/10 px-3 py-1.5 rounded-lg flex items-center justify-between max-w-[85%] italic">
                    <div className="flex items-center space-x-1.5 truncate">
                      <span className="font-bold">📂 Trace:</span>
                      <span className="truncate">{msg.citation}</span>
                    </div>
                    {msg.confidence !== undefined && (
                      <span className="ml-2 font-mono not-italic bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded text-[9px] font-bold">
                        {msg.confidence}% Grounded
                      </span>
                    )}
                  </div>
                )}

                {msg.sender === 'system' && msg.logId && (
                  <div className="flex items-center space-x-3 text-[10px] text-slate-500 px-1 pt-1">
                    <span>Was this answer accurate?</span>
                    <button
                      onClick={() => handleFeedback(msg.logId, 1, i)}
                      className={`px-2 py-0.5 rounded transition-all cursor-pointer font-bold ${
                        msg.rating === 1 ? 'bg-emerald-600 text-white' : 'bg-slate-900 hover:bg-slate-800 text-slate-300'
                      }`}
                    >
                      👍 {msg.rating === 1 ? 'Helpful' : 'Yes'}
                    </button>
                    <button
                      onClick={() => handleFeedback(msg.logId, -1, i)}
                      className={`px-2 py-0.5 rounded transition-all cursor-pointer font-bold ${
                        msg.rating === -1 ? 'bg-rose-600 text-white' : 'bg-slate-900 hover:bg-slate-800 text-slate-300'
                      }`}
                    >
                      👎 {msg.rating === -1 ? 'Unhelpful' : 'No'}
                    </button>
                  </div>
                )}
              </div>
            ))}
            
            {queryLoading && (
              <div className="text-slate-500 italic animate-pulse flex items-center space-x-2">
                <span>⚡ Interrogating localized vector clusters...</span>
              </div>
            )}
          </div>

          {/* Input Submission Terminal Strip */}
          <form onSubmit={handleAskRAGCore} className="p-4 bg-slate-900/20 border-t border-slate-800/80 flex items-center space-x-3">
            <input
              type="text"
              placeholder="Ask an infrastructure compliance question across all active registries..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={queryLoading}
              className="flex-1 bg-slate-950 text-slate-200 border border-slate-800 rounded-xl px-4 py-3 text-xs font-mono placeholder-slate-600 focus:outline-none focus:border-indigo-500 shadow-inner"
            />
            <button
              type="submit"
              disabled={queryLoading || !chatInput.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-900 disabled:text-slate-600 text-white font-extrabold text-[10px] tracking-widest uppercase px-5 py-3 rounded-xl shadow-lg transition-all active:scale-95 cursor-pointer"
            >
              Query
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default KnowledgeHubView;