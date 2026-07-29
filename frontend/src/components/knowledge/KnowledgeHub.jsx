// src/components/knowledge/KnowledgeHub.jsx

import { useState, useEffect, useCallback, useRef } from 'react';
import ChatHistorySidebar from '../ChatHistorySidebar';
import {
  fetchKnowledgeFilesApi,
  uploadKnowledgeFilesApi,
  deleteKnowledgeFileApi,
  createKnowledgeArticleApi,
  deleteKnowledgeArticleApi,
  runAgentQueryApi,
  exportPdfReportApi,
} from '../../services/api';

export default function KnowledgeHub({
  items = [],
  onAddArticle,
  onLoadSampleKnowledge,
  onRefresh,
  onIngestionComplete,
}) {
  const [activeView, setActiveView] = useState('documents'); // 'documents' | 'articles'
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Upload toast notification: { type: 'info'|'success'|'error', message: string } | null
  const [uploadToast, setUploadToast] = useState(null);
  // Ref for the delayed-refetch timers (array) so all can be cleared on unmount
  const refetchTimerRef = useRef([]);

  // Runbook / Article State
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [showAddModal, setShowAddModal] = useState(false);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('RUNBOOK');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Chat History Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeChatId, setActiveChatId] = useState(null);
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);

  // Multi-Agent RAG Chat State
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [agentStep, setAgentStep] = useState('');
  const [exportingPdf, setExportingPdf] = useState(null);

  // Fetch uploaded documents list
  const fetchFiles = useCallback(async () => {
    setLoadingFiles(true);
    try {
      const { data } = await fetchKnowledgeFilesApi();
      const rawFiles = Array.isArray(data) ? data : (data?.files || data?.data || []);
      // console.log("[KnowledgeHub] Loaded files for rendering:", rawFiles);
      setUploadedFiles(rawFiles);
    } catch (err) {
      console.error('Failed to fetch files:', err);
    } finally {
      setLoadingFiles(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Auto-dismiss upload toast after 5 seconds
  const showToast = useCallback((type, message) => {
    setUploadToast({ type, message });
    setTimeout(() => setUploadToast(null), 5000);
  }, []);

  // Clear ALL pending refetch timers when the component unmounts
  useEffect(() => {
    return () => {
      refetchTimerRef.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  // File Upload Handler (Drag & Drop + Input File)
  const handleFileUpload = async (filesList) => {
    if (!filesList || filesList.length === 0) return;
    setUploading(true);

    try {
      const { data } = await uploadKnowledgeFilesApi(filesList);

      // Reset the file input so the same file can be re-selected if needed
      if (fileInputRef.current) fileInputRef.current.value = '';

      // Determine the detail message from the response
      const detail =
        data?.detail ||
        (data?.status === 'processing'
          ? 'Document queued for background vector indexing.'
          : 'Upload successful.');

      // Show the "queued" info banner immediately
      showToast('info', `📄 ${data?.filename || 'File'} — ${detail}`);

      // Fetch immediately so the new row (status=Processing) appears at once
      fetchFiles();
      if (onRefresh) onRefresh();

      // Cancel any in-flight poll timers from a previous upload
      refetchTimerRef.current.forEach((t) => clearTimeout(t));
      refetchTimerRef.current = [];

      // Progressive multi-stage poll (at 2s and 6s) to capture shift from Processing to Indexed
      [2000, 6000, 12000].forEach((delay) => {
        const t = setTimeout(() => {
          fetchFiles();
          if (delay === 12000 && onIngestionComplete) onIngestionComplete();
        }, delay);
        refetchTimerRef.current.push(t);
      });

    } catch (err) {
      console.error('Upload error:', err);
      // Reset input even on failure so the user can retry
      if (fileInputRef.current) fileInputRef.current.value = '';
      showToast('error', `Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      setIsDragOver(false);
    }
  };

  const handleDeleteFile = async (fileId, filename) => {
    if (!window.confirm(`Delete document "${filename}" and purge all vectorized chunks?`)) return;

    try {
      const { ok } = await deleteKnowledgeFileApi(fileId);
      if (ok) {
        setUploadedFiles((prev) => prev.filter((f) => (f.id || f.job_id) !== fileId));
      } else {
        alert('Failed to delete document.');
      }
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  // Multi-Agent RAG Query
  const handleAgentQuery = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || queryLoading) return;

    const userQuery = chatInput.trim();
    setChatMessages((prev) => [...prev, { sender: 'user', text: userQuery }]);
    setChatInput('');
    setQueryLoading(true);

    // Simulate Agent Thinking Pipeline Sequence
    setAgentStep('🧠 Planner Agent: Decomposing user intent into execution plan...');
    const t1 = setTimeout(() => {
      setAgentStep('🔍 Hybrid Retrieval Agent: Running BM25 + ChromaDB vector search...');
    }, 800);
    const t2 = setTimeout(() => {
      setAgentStep('🛡️ Verification Agent: Checking response groundedness & computing citations...');
    }, 1800);
    const t3 = setTimeout(() => {
      setAgentStep('📊 Report Agent: Formatting Executive Summary & structured output...');
    }, 2800);

    try {
      const { ok, data } = await runAgentQueryApi(userQuery);

      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);

      if (ok && data) {
        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'ai',
            text: data.answer,
            citations: data.citations || [],
            confidence_score: data.confidence_score,
            execution_plan: data.execution_plan,
            is_grounded: data.is_grounded,
            query: userQuery,
          },
        ]);
      } else {
        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'ai',
            text: data?.message || 'No response returned.',
            citations: [],
            confidence_score: 50,
            execution_plan: 'Single-pass RAG fallback execution.',
            query: userQuery,
          },
        ]);
      }
    } catch (err) {
      console.error('Agent Query Error:', err);
      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: `⚠️ Query processing exception: ${err.message}`,
          citations: [],
          confidence_score: 0,
          query: userQuery,
        },
      ]);
    } finally {
      setQueryLoading(false);
      setAgentStep('');
      // Auto-refresh the Chat History Sidebar after each query
      setSidebarRefreshTrigger((n) => n + 1);
    }
  };

  // PDF Export Download Trigger
  const handleExportPdf = async (msgIndex, msg) => {
    setExportingPdf(msgIndex);
    try {
      const blob = await exportPdfReportApi(
        msg.query || 'Enterprise Query',
        msg.text,
        msg.citations || [],
        msg.confidence_score || 0
      );

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GuardCore_Report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
      alert(`PDF Export Error: ${err.message}`);
    } finally {
      setExportingPdf(null);
    }
  };

  // Runbook / Article Add Handler
  const handleAddSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;

    setSubmitting(true);
    const newArticle = {
      title: title.trim(),
      category,
      author: 'Current User',
      content: content.trim(),
    };

    try {
      const { ok } = await createKnowledgeArticleApi(newArticle);
      if (ok) {
        if (onRefresh) onRefresh();
      } else {
        if (onAddArticle) {
          onAddArticle({
            ...newArticle,
            id: Date.now(),
            created_at: new Date().toISOString().split('T')[0],
          });
        }
      }
    } catch {
      if (onAddArticle) {
        onAddArticle({
          ...newArticle,
          id: Date.now(),
          created_at: new Date().toISOString().split('T')[0],
        });
      }
    } finally {
      setTitle('');
      setContent('');
      setShowAddModal(false);
      setSubmitting(false);
    }
  };

  // runbook / article delete handler
  const handleDeleteArticle = async (item) => {
    const resolvedId = item.id || item._id || item.title;
    const displayName = item.title || resolvedId;
    if (!window.confirm(`Delete runbook "${displayName}"?`)) return;

    try {
      const { ok } = await deleteKnowledgeArticleApi(resolvedId);
      if (ok) {
        // Re-sync the parent's list from the server
        if (onRefresh) onRefresh();
      } else {
        alert('Failed to delete runbook.');
      }
    } catch (err) {
      console.error('Delete article error:', err);
    }
  };
  
  const filteredItems = items.filter((item) => {
    const matchesCat = categoryFilter === 'ALL' || item.category === categoryFilter;
    const matchesSearch =
      (item.title && item.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (item.content && item.content.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesSearch;
  });

  // Chat sidebar handlers
  const handleNewChat = () => {
    setChatMessages([]);
    setChatInput('');
    setActiveChatId(null);
  };

  const handleLoadSession = (session) => {
    // Replay the session's Q&A into chat
    const replayed = [
      { sender: 'user', text: session.query || '' },
      {
        sender: 'ai',
        text: session.answer || '(No answer recorded)',
        citations: [],
        confidence_score: session.confidence_score ?? null,
        execution_plan: '',
        query: session.query || '',
      },
    ];
    setChatMessages(replayed);
    setActiveChatId(session.id);
    setChatInput('');
  };

  return (
    <div className="space-y-6">
      {/* Upload feedback toast banner */}
      {uploadToast && (
        <div
          className={`flex items-start gap-3 px-4 py-3 rounded-xl border text-xs font-medium transition-all ${
            uploadToast.type === 'error'
              ? 'bg-rose-950/80 border-rose-700 text-rose-300'
              : uploadToast.type === 'success'
              ? 'bg-emerald-950/80 border-emerald-700 text-emerald-300'
              : 'bg-cyan-950/80 border-cyan-700 text-cyan-200'
          }`}
        >
          <span className="shrink-0 text-base leading-none mt-0.5">
            {uploadToast.type === 'error' ? '⚠️' : uploadToast.type === 'success' ? '✅' : '⏳'}
          </span>
          <span className="flex-1">{uploadToast.message}</span>
          <button
            onClick={() => setUploadToast(null)}
            className="shrink-0 opacity-60 hover:opacity-100 transition-opacity ml-2 text-sm leading-none"
            aria-label="Dismiss notification"
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Header & Sub-Nav */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            🤖 Multi-Agent Enterprise RAG Hub
          </h2>
          <p className="text-xs text-slate-400">
            Ingest PDF, DOCX, XLSX, TXT documents with hybrid retrieval, grounded citations & PDF exports.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex bg-slate-950 border border-slate-800 rounded-lg p-1 space-x-1 text-xs">
            <button
              onClick={() => setActiveView('documents')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                activeView === 'documents'
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📄 Documents ({uploadedFiles.length})
            </button>
            <button
              onClick={() => setActiveView('articles')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                activeView === 'articles'
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📚 Runbooks ({items.length})
            </button>
          </div>

          <button
            onClick={onLoadSampleKnowledge}
            className="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-400 hover:text-cyan-300 border border-slate-700 rounded-lg transition-colors cursor-pointer"
            title="Populate sample runbooks and compliance articles"
          >
            ⚡ Load Sample Articles
          </button>

          {activeView === 'articles' && (
            <button
              onClick={() => setShowAddModal(!showAddModal)}
              className="px-3.5 py-1.5 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
            >
              {showAddModal ? 'Close Form' : '+ Add Article'}
            </button>
          )}
        </div>
      </div>

      {/* VIEW 1: DOCUMENTS MANAGEMENT & DRAG-DROP INGESTION */}
      {activeView === 'documents' && (
        <div className="space-y-6">
          {/* Drag and Drop Upload Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              handleFileUpload(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              isDragOver
                ? 'border-cyan-400 bg-cyan-950/30'
                : 'border-slate-800 hover:border-cyan-700 bg-slate-950/40'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt"
              onChange={(e) => handleFileUpload(e.target.files)}
              className="hidden"
            />
            <div className="text-4xl mb-3">📁</div>
            <h3 className="text-sm font-bold text-slate-200 mb-1">
              {uploading ? 'Processing & Vectorizing Documents...' : 'Drag & Drop Enterprise Documents Here'}
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mb-3">
              Supports <span className="text-cyan-400">PDF, DOCX, XLSX, CSV, and TXT</span>. Documents will be chunked, embedded into ChromaDB with tenant isolation, and indexed for hybrid search.
            </p>
            <button
              type="button"
              disabled={uploading}
              className="px-4 py-2 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {uploading ? 'Parsing & Indexing...' : 'Browse Files'}
            </button>
          </div>

          {/* Uploaded Files Grid / Table */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-slate-200">
                Indexed Documents ({uploadedFiles.length})
              </h3>
              <button
                onClick={fetchFiles}
                className="text-xs text-slate-400 hover:text-cyan-400 flex items-center gap-1"
              >
                🔄 Refresh List
              </button>
            </div>

            {loadingFiles ? (
              <div className="text-center py-8 text-slate-500 text-xs animate-pulse">
                Loading knowledge document registry...
              </div>
            ) : uploadedFiles.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                No documents uploaded yet. Drag & drop files above to start querying your data.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                      <th className="py-2.5 px-3">Filename</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Size</th>
                      <th className="py-2.5 px-3">Chunks</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {uploadedFiles.map((file, index) => {
                      const fileName = file.filename || file.name || file.title || 'Unnamed File';
                      const fileSize = file.file_size || file.size || 0;
                      const fileStatus = file.status || 'Processing';
                      const fileId = file.id || file.job_id || index;
                      const normalizedStatus = String(fileStatus).toLowerCase();

                      return (
                        <tr key={fileId} className="hover:bg-slate-900/40 transition-colors">
                          <td className="py-3 px-3 font-medium text-slate-200">
                            📄 {fileName}
                          </td>
                          <td className="py-3 px-3 font-mono text-cyan-400">
                            {file.file_type || 'DOC'}
                          </td>
                          <td className="py-3 px-3 text-slate-400 font-mono">
                            {fileSize ? `${(fileSize / 1024).toFixed(1)} KB` : '—'}
                          </td>
                          <td className="py-3 px-3 text-slate-300 font-mono">
                            {file.chunk_count || 'Auto'}
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                                normalizedStatus === 'indexed'
                                  ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                                  : normalizedStatus === 'processing'
                                  ? 'bg-amber-950 text-amber-400 border-amber-800 animate-pulse'
                                  : 'bg-rose-950 text-rose-400 border-rose-800'
                              }`}
                            >
                              {fileStatus}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() => handleDeleteFile(fileId, fileName)}
                              className="px-2.5 py-1 text-[11px] text-rose-400 hover:text-rose-300 hover:bg-rose-950/60 border border-rose-900/50 rounded transition-colors"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 2: RUNBOOKS & ARTICLES */}
      {activeView === 'articles' && (
        <div className="space-y-6">
          {showAddModal && (
            <form onSubmit={handleAddSubmit} className="p-6 bg-slate-950 border border-slate-800 rounded-xl space-y-4">
              <h3 className="text-sm font-bold text-white">Create New Knowledge Article</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Article Title</label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Redis Sentinel Failover Protocol"
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="RUNBOOK">RUNBOOK</option>
                    <option value="INCIDENT">INCIDENT</option>
                    <option value="COMPLIANCE">COMPLIANCE</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Content / Resolution Steps</label>
                <textarea
                  rows="3"
                  required
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Detailed troubleshooting guidance..."
                  className="w-full p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg"
                >
                  Save Article
                </button>
              </div>
            </form>
          )}

          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row justify-between gap-3">
              <input
                type="text"
                placeholder="Filter articles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 w-full sm:w-64 focus:outline-none focus:border-cyan-500"
              />
              <div className="flex bg-slate-950 border border-slate-800 rounded-lg p-1 space-x-1 text-xs">
                {['ALL', 'RUNBOOK', 'INCIDENT', 'COMPLIANCE'].map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategoryFilter(cat)}
                    className={`px-3 py-1 rounded text-[10px] font-semibold transition-colors ${
                      categoryFilter === cat
                        ? 'bg-slate-800 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {filteredItems.length === 0 ? (
              <div className="p-8 text-center border border-slate-800 rounded-xl bg-slate-950/40 space-y-3">
                <div className="text-3xl">📚</div>
                <h3 className="text-sm font-bold text-slate-200">No Runbook Articles Found</h3>
                <button
                  onClick={onLoadSampleKnowledge}
                  className="px-4 py-2 text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
                >
                  ⚡ Load Sample Articles
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredItems.map((item) => (
                  <div key={item.id || item._id || item.title} className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                    <div className="flex justify-between items-start">
                      <h3 className="text-sm font-bold text-white flex-1 mr-3">{item.title || item.file_name}</h3>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800 px-2 py-0.5 rounded uppercase">
                          {item.category || 'DOC'}
                        </span>
                        <button
                          onClick={() => handleDeleteArticle(item)}
                          className="px-2 py-1 text-[11px] font-bold bg-red-500/10 hover:bg-red-500/25 text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/60 rounded-lg transition-all cursor-pointer inline-flex items-center gap-1"
                          title="Delete this runbook"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                    <p className="text-xs font-mono text-slate-300 leading-relaxed">
                      {item.content || item.summary}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MULTI-AGENT CHAT & CITATION VISUALIZER (ALWAYS VISIBLE BOTTOM PANEL) */}
      <div className="flex gap-4 items-stretch">
        {/* Chat History Sidebar */}
        <ChatHistorySidebar
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen((v) => !v)}
          onNewChat={handleNewChat}
          onLoadSession={handleLoadSession}
          activeChatId={activeChatId}
          refreshTrigger={sidebarRefreshTrigger}
        />

        {/* Main Chat Console */}
        <div className="flex-1 bg-slate-950/70 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <span className="text-lg">🤖</span>
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                Multi-Agent RAG Intelligence Console
              </h3>
            </div>
            <span className="text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800/60 px-2.5 py-0.5 rounded-full">
              Planner • Hybrid Retrieval • Verifier • Reporter
            </span>
          </div>

          {/* Chat Message Trajectory */}
          <div className="space-y-4 max-h-96 overflow-y-auto p-4 bg-slate-900/60 border border-slate-800/80 rounded-lg">
            {chatMessages.length === 0 ? (
              <div className="text-center py-10 text-slate-500 text-xs font-mono space-y-2">
                <p className="text-slate-400">Ask any complex question over your ingested documents.</p>
                <p className="text-[11px] text-slate-600">
                  Example: "What are our compliance guidelines for database connection pool exhaustion?"
                </p>
              </div>
            ) : (
              chatMessages.map((msg, idx) => (
                <div key={idx} className="space-y-2">
                  {msg.sender === 'user' ? (
                    <div className="flex justify-end">
                      <div className="bg-cyan-950/80 text-cyan-200 border border-cyan-800/60 p-3 rounded-xl text-xs max-w-xl font-sans">
                        <span className="text-[9px] font-mono text-cyan-400 uppercase block mb-1">User Query</span>
                        {msg.text}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-3">
                      {/* Header bar with Confidence Badge & Export PDF */}
                      <div className="flex justify-between items-center border-b border-slate-800/60 pb-2">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-bold text-cyan-400 font-mono">
                            ⚡ AI Executive Summary
                          </span>
                          {typeof msg.confidence_score === 'number' && (
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                                msg.confidence_score >= 70
                                  ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                                  : msg.confidence_score >= 40
                                  ? 'bg-amber-950 text-amber-400 border-amber-800'
                                  : 'bg-rose-950 text-rose-400 border-rose-800'
                              }`}
                            >
                              Confidence: {msg.confidence_score}%
                            </span>
                          )}
                        </div>

                        <button
                          onClick={() => handleExportPdf(idx, msg)}
                          disabled={exportingPdf === idx}
                          className="px-3 py-1 text-[11px] font-semibold bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 rounded-md transition-colors flex items-center gap-1 disabled:opacity-50"
                        >
                          {exportingPdf === idx ? 'Generating PDF...' : '📥 Download PDF Report'}
                        </button>
                      </div>

                      {/* Answer text */}
                      <div className="text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
                        {msg.text}
                      </div>

                      {/* Execution Plan details */}
                      {msg.execution_plan && (
                        <div className="text-[10px] font-mono bg-slate-900/80 p-2.5 rounded border border-slate-800 text-slate-400">
                          <span className="text-cyan-400 font-bold">🧠 Execution Plan:</span> {msg.execution_plan}
                        </div>
                      )}

                      {/* Source Citation Cards */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
                          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                            📌 Grounded Source Citations ({msg.citations.length})
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                            {msg.citations.map((cit, cIdx) => (
                              <div
                                key={cIdx}
                                className="p-2.5 bg-slate-900/90 border border-slate-800 rounded-lg text-[11px] space-y-1 font-mono hover:border-cyan-800 transition-colors"
                              >
                                <div className="flex justify-between items-center text-cyan-300 font-semibold truncate">
                                  <span className="truncate">📄 {cit.filename}</span>
                                  <span className="text-[9px] bg-slate-800 px-1.5 py-0.2 rounded text-slate-300">
                                    p. {cit.page}
                                  </span>
                                </div>
                                <p className="text-[10px] text-slate-400 line-clamp-2 leading-tight italic">
                                  "{cit.snippet}"
                                </p>
                                {cit.score && (
                                  <div className="text-[9px] text-emerald-400 pt-0.5">
                                    Match Overlap: {cit.score}%
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}

            {/* Active Agent Thinking Banner */}
            {queryLoading && (
              <div className="p-3 bg-cyan-950/40 border border-cyan-800/50 rounded-lg text-xs font-mono text-cyan-300 flex items-center gap-3 animate-pulse">
                <span className="text-base">⚙️</span>
                <span>{agentStep || 'Multi-agent system orchestrating query...'}</span>
              </div>
            )}
          </div>

          {/* Input Form */}
          <form onSubmit={handleAgentQuery} className="flex gap-2">
            <input
              type="text"
              placeholder="Ask a question across your enterprise documents..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              className="flex-1 px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-sans"
            />
            <button
              type="submit"
              disabled={queryLoading || !chatInput.trim()}
              className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition-colors"
            >
              {queryLoading ? 'Processing...' : 'Run Query'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
