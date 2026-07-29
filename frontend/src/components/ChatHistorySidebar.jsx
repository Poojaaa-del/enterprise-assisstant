// frontend/src/components/ChatHistorySidebar.jsx
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

// Groups sessions into Today / Yesterday / Previous 7 Days
function groupSessionsByDate(sessions) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart - 86400000);
  const sevenDaysStart = new Date(todayStart - 6 * 86400000);

  const groups = { today: [], yesterday: [], previous: [] };

  sessions.forEach((s) => {
    const created = new Date(s.created_at);
    if (created >= todayStart) {
      groups.today.push(s);
    } else if (created >= yesterdayStart) {
      groups.yesterday.push(s);
    } else if (created >= sevenDaysStart) {
      groups.previous.push(s);
    }
    // older items are omitted intentionally
  });

  return groups;
}

// Truncates a query string to a display title
const truncate = (str, n = 42) => (str && str.length > n ? str.slice(0, n) + '…' : str);

export default function ChatHistorySidebar({
  isOpen,
  onToggle,
  onNewChat,
  onLoadSession,
  activeChatId,
  refreshTrigger,
}) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState('');

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/history`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      } else if (res.status === 401) {
        setError('Session expired. Please sign in again.');
      } else {
        setSessions([]);
      }
    } catch (err) {
      console.warn('[ChatHistorySidebar] Failed to fetch history:', err);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, fetchHistory]);

  // Auto-refresh when a new query completes (refreshTrigger increments)
  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchHistory();
    }
  }, [refreshTrigger, fetchHistory]);

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    setDeletingId(sessionId);
    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/history/${sessionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      }
    } catch (err) {
      console.error('[ChatHistorySidebar] Delete failed:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleLoadSession = (session) => {
    if (onLoadSession) onLoadSession(session);
  };

  const groups = groupSessionsByDate(sessions);
  const hasAny = groups.today.length + groups.yesterday.length + groups.previous.length > 0;

  return (
    <div
      id="chat-history-sidebar"
      className="relative flex flex-col transition-all duration-300 ease-in-out shrink-0"
      style={{ width: isOpen ? '260px' : '44px' }}
    >
      {/* Toggle button (always visible) */}
      <button
        id="sidebar-toggle-btn"
        onClick={onToggle}
        title={isOpen ? 'Collapse history' : 'Open history'}
        className="absolute -right-3 top-4 z-10 w-6 h-6 rounded-full border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-all shadow-lg"
        style={{ background: 'rgb(15,23,42)' }}
      >
        {isOpen ? (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
        ) : (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
          </svg>
        )}
      </button>

      {/* Collapsed strip */}
      {!isOpen && (
        <div
          className="flex flex-col items-center pt-4 pb-4 space-y-4 h-full rounded-xl border border-slate-800/80 cursor-pointer"
          style={{ background: 'rgba(15,23,42,0.80)' }}
          onClick={onToggle}
          title="Open chat history"
        >
          <span className="text-[9px] font-bold uppercase tracking-widest text-slate-600 [writing-mode:vertical-rl] rotate-180">
            History
          </span>
          <span className="text-slate-600 text-xs">📋</span>
        </div>
      )}

      {/* Expanded panel */}
      {isOpen && (
        <div
          className="flex flex-col h-full rounded-xl border border-slate-800/80 overflow-hidden"
          style={{ background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(8px)' }}
        >
          {/* Panel Header */}
          <div className="px-3 py-3 border-b border-slate-800/80 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-1.5">
              <span className="text-xs">📋</span>
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                Chat History
              </span>
            </div>
            <button
              id="refresh-history-btn"
              onClick={fetchHistory}
              disabled={loading}
              className="p-1 text-slate-600 hover:text-slate-300 transition-colors disabled:opacity-40"
              title="Refresh history"
            >
              <svg className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>

          {/* New Chat Button */}
          <div className="px-3 py-2.5 shrink-0">
            <button
              id="new-chat-btn"
              onClick={onNewChat}
              className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg text-xs font-semibold border transition-all active:scale-95"
              style={{
                background: 'linear-gradient(135deg, rgba(6,182,212,0.15) 0%, rgba(99,102,241,0.15) 100%)',
                borderColor: 'rgba(99,102,241,0.30)',
                color: '#a5b4fc',
              }}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              <span>New Chat</span>
            </button>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-1 scrollbar-thin scrollbar-thumb-slate-800">
            {loading && (
              <div className="px-2 py-6 text-center">
                <div className="flex items-center justify-center space-x-2 text-slate-600">
                  <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span className="text-[10px] font-mono">Loading history...</span>
                </div>
              </div>
            )}

            {!loading && error && (
              <div className="px-2 py-4 text-center text-[10px] text-rose-400 font-mono">{error}</div>
            )}

            {!loading && !error && !hasAny && (
              <div className="px-2 py-8 text-center space-y-2">
                <div className="text-2xl">💬</div>
                <p className="text-[10px] text-slate-600 font-mono leading-relaxed">
                  No chat history yet.
                  <br />Start a query to see it here.
                </p>
              </div>
            )}

            {!loading && !error && hasAny && (
              <>
                {groups.today.length > 0 && (
                  <SessionGroup
                    label="Today"
                    sessions={groups.today}
                    activeChatId={activeChatId}
                    deletingId={deletingId}
                    onLoad={handleLoadSession}
                    onDelete={handleDeleteSession}
                  />
                )}
                {groups.yesterday.length > 0 && (
                  <SessionGroup
                    label="Yesterday"
                    sessions={groups.yesterday}
                    activeChatId={activeChatId}
                    deletingId={deletingId}
                    onLoad={handleLoadSession}
                    onDelete={handleDeleteSession}
                  />
                )}
                {groups.previous.length > 0 && (
                  <SessionGroup
                    label="Previous 7 Days"
                    sessions={groups.previous}
                    activeChatId={activeChatId}
                    deletingId={deletingId}
                    onLoad={handleLoadSession}
                    onDelete={handleDeleteSession}
                  />
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SessionGroup({ label, sessions, activeChatId, deletingId, onLoad, onDelete }) {
  return (
    <div>
      <p className="px-2 py-1.5 text-[9px] font-bold uppercase tracking-[0.12em] text-slate-600">
        {label}
      </p>
      {sessions.map((session) => {
        const isActive = activeChatId === session.id;
        const isDeleting = deletingId === session.id;
        return (
          <div
            key={session.id}
            id={`session-item-${session.id}`}
            role="button"
            tabIndex={0}
            onClick={() => onLoad(session)}
            onKeyDown={(e) => e.key === 'Enter' && onLoad(session)}
            className="group flex items-start justify-between px-2 py-2 rounded-lg cursor-pointer transition-all mb-0.5"
            style={isActive
              ? { background: 'rgba(99,102,241,0.18)', borderLeft: '2px solid rgba(99,102,241,0.60)' }
              : { background: 'transparent', borderLeft: '2px solid transparent' }
            }
            onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'rgba(30,41,59,0.60)'; }}
            onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
          >
            <div className="min-w-0 flex-1 pr-1">
              <p
                className="text-[11px] leading-tight font-medium truncate"
                style={{ color: isActive ? '#a5b4fc' : '#94a3b8' }}
              >
                {truncate(session.query)}
              </p>
              <p className="text-[9px] text-slate-600 font-mono mt-0.5">
                {typeof session.confidence_score === 'number'
                  ? `Confidence: ${session.confidence_score}%`
                  : formatRelativeTime(session.created_at)}
              </p>
            </div>

            {/* Delete button */}
            <button
              id={`delete-session-${session.id}`}
              onClick={(e) => onDelete(e, session.id)}
              disabled={isDeleting}
              title="Delete session"
              className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded text-slate-600 hover:text-rose-400 hover:bg-rose-950/30 disabled:opacity-40 mt-0.5"
            >
              {isDeleting ? (
                <svg className="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              ) : (
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              )}
            </button>
          </div>
        );
      })}
    </div>
  );
}

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return '';
  }
}
