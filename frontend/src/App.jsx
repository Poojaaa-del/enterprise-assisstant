// src/App.jsx

import { useState, useEffect, useCallback } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import AccountModal from './components/AccountModal';
import AuthScreen from './components/auth/AuthScreen';
import VerifyEmailPage from './components/auth/VerifyEmailPage';
import TriageConsole from './components/triage/TriageConsole';
import KnowledgeHub from './components/knowledge/KnowledgeHub';
import HistoryTable from './components/history/HistoryTable';
import { GOOGLE_CLIENT_ID, SAMPLE_ARTICLES } from './utils/constants';
import { getStoredToken, setStoredToken, removeStoredToken, parseJwt } from './utils/auth';
import {
  fetchHistoryApi,
  fetchKnowledgeArticlesApi,
  deleteLogApi,
  escalateIncidentApi,
  ingestSampleArticlesApi,
} from './services/api';

export default function App() {
  const [token, setToken] = useState(getStoredToken);
  const [history, setHistory] = useState([]);
  const [knowledgeItems, setKnowledgeItems] = useState([]);
  const [activeTab, setActiveTab] = useState('triage');
  const [loading, setLoading] = useState(false);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [userInfo, setUserInfo] = useState(() => (token ? parseJwt(token) || {} : null));
  const [ingestionComplete, setIngestionComplete] = useState(false);
  const isVerifyEmailRoute = window.location.pathname === '/verify-email';

  const handleLogout = useCallback(() => {
    removeStoredToken();
    setToken(null);
    setHistory([]);
    setKnowledgeItems([]);
    setUserInfo(null);
    setShowAccountModal(false);
  }, []);

  const handleLoginSuccess = (newToken) => {
    setStoredToken(newToken);
    setToken(newToken);
    setUserInfo(parseJwt(newToken) || {});
  };

  const fetchHistory = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const { status, data } = await fetchHistoryApi();
      if (status === 401) {
        handleLogout();
        return;
      }
      setHistory(data);
    } catch {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, [token, handleLogout]);

  const fetchKnowledge = useCallback(async () => {
    if (!token) return;
    try {
      const { status, data } = await fetchKnowledgeArticlesApi();
      if (status === 401) {
        handleLogout();
        return;
      }
      setKnowledgeItems(data);
    } catch {
      setKnowledgeItems([]);
    }
  }, [token, handleLogout]);

  useEffect(() => {
    if (token) {
      queueMicrotask(() => {
        fetchHistory();
        fetchKnowledge();
      });
    }
  }, [token, fetchHistory, fetchKnowledge]);

  const handleLoadSampleArticles = async () => {
    try {
      await ingestSampleArticlesApi(SAMPLE_ARTICLES);
      fetchKnowledge();
      alert('✅ Sample runbooks & articles ingested successfully into Knowledge Hub!');
    } catch (err) {
      console.error('Error loading sample articles:', err);
      SAMPLE_ARTICLES.forEach((art, idx) => {
        setKnowledgeItems((prev) => [
          { ...art, id: Date.now() + idx, created_at: new Date().toISOString().split('T')[0] },
          ...prev,
        ]);
      });
      alert('✅ Sample articles loaded locally!');
    }
  };

  const handleDeleteLog = async (logId) => {
    if (!logId) return;
    if (!window.confirm(`Are you sure you want to permanently purge Log Record #${logId}?`)) return;

    setHistory((prev) => prev.filter((item) => (item.id ?? item._id ?? item.log_id) !== logId));

    const isClientOnlyId =
      (typeof logId === 'string' && (logId.startsWith('local_') || logId.startsWith('temp_'))) ||
      (typeof logId === 'number' && logId > 1e11);

    if (isClientOnlyId) return;

    try {
      const { status } = await deleteLogApi(logId);
      if (status === 401) handleLogout();
    } catch (error) {
      console.error('Failed to delete record:', error);
    }
  };

  const handleEscalateRow = async (logId) => {
    if (!logId || logId === 'N/A') return;
    const numericId = parseInt(logId, 10);
    if (isNaN(numericId)) return;

    setHistory((prev) =>
      prev.map((item) =>
        (item.id === numericId || item._id === numericId || item.log_id === numericId)
          ? { ...item, status: 'MANDATORY' }
          : item
      )
    );

    const isClientOnlyId =
      (typeof logId === 'string' && (logId.startsWith('local_') || logId.startsWith('temp_'))) ||
      (typeof logId === 'number' && logId > 1e11);

    if (isClientOnlyId) return;

    try {
      const { status, ok } = await escalateIncidentApi(numericId);
      if (status === 401) {
        handleLogout();
        return;
      }
      if (ok) fetchHistory();
    } catch (error) {
      console.error('Escalation error:', error);
    }
  };

  if (isVerifyEmailRoute) {
    return <VerifyEmailPage />;
  }

  if (!token) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <AuthScreen onLoginSuccess={handleLoginSuccess} />
      </GoogleOAuthProvider>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              LogTriage AI
            </span>
            <span className="text-xs bg-cyan-950 text-cyan-400 border border-cyan-800/50 px-2 py-0.5 rounded-full font-mono">
              v1.0
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              id="notification-bell-btn"
              title={ingestionComplete ? 'Ingestion complete!' : 'No new notifications'}
              onClick={() => setIngestionComplete(false)}
              className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {ingestionComplete && <span className="absolute top-1 right-1 w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />}
            </button>

            <button
              id="user-profile-pill-btn"
              onClick={() => setShowAccountModal(true)}
              title="Account Settings"
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-slate-700/80 hover:bg-slate-800 transition-all group cursor-pointer"
              style={{ background: 'rgba(30,41,59,0.60)' }}
            >
              {userInfo?.picture ? (
                <img src={userInfo.picture} alt="avatar" className="w-6 h-6 rounded-full border border-indigo-500/40 object-cover" />
              ) : (
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black text-white shrink-0 bg-gradient-to-r ${userInfo?.avatar_color || 'from-cyan-500 to-blue-600'}`}>
                  {(userInfo?.full_name || userInfo?.username || userInfo?.email || 'U').split(' ').map((n) => n[0]?.toUpperCase()).slice(0, 2).join('')}
                </div>
              )}
              <span className="text-xs font-medium text-slate-300 group-hover:text-white transition-colors max-w-[120px] truncate">
                {userInfo?.full_name || userInfo?.username || userInfo?.email?.split('@')[0] || 'Account'}
              </span>
              <span className="hidden sm:inline-block text-[9px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 px-1.5 py-0.2 rounded">
                {userInfo?.department || 'Engineering'}
              </span>
              <svg className="w-3 h-3 text-slate-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <button onClick={handleLogout} className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-700 transition-colors">
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {showAccountModal && (
        <AccountModal
          userInfo={userInfo}
          onClose={() => setShowAccountModal(false)}
          onUpdateUser={(updatedUser, newToken) => {
            if (newToken) handleLoginSuccess(newToken);
            if (updatedUser) setUserInfo((prev) => ({ ...prev, ...updatedUser }));
          }}
        />
      )}

      {/* Main Layout Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex border-b border-slate-800 space-x-6">
          <button onClick={() => setActiveTab('triage')} className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'triage' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
            🖥️ Triage Console
          </button>
          <button onClick={() => setActiveTab('knowledge')} className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'knowledge' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
            📚 Knowledge Hub ({knowledgeItems.length})
          </button>
          <button onClick={() => setActiveTab('history')} className={`pb-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'history' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
            📋 Incident History ({history.length})
          </button>
        </div>

        {activeTab === 'triage' && (
          <TriageConsole history={history} onIngestSuccess={(newLog) => setHistory((prev) => [newLog, ...prev])} />
        )}
        {activeTab === 'knowledge' && (
          <KnowledgeHub
            items={knowledgeItems}
            onAddArticle={(art) => setKnowledgeItems((prev) => [art, ...prev])}
            onRefresh={fetchKnowledge}
            onLoadSampleKnowledge={handleLoadSampleArticles}
            onIngestionComplete={() => {
              setIngestionComplete(true);
              setTimeout(() => setIngestionComplete(false), 8000);
            }}
          />
        )}
        {activeTab === 'history' && (
          <HistoryTable history={history} loading={loading} onDelete={handleDeleteLog} onEscalate={handleEscalateRow} onGenerateStarterLog={fetchHistory} />
        )}
      </main>
    </div>
  );
}
