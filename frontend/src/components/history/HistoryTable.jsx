// src/components/history/HistoryTable.jsx

import { useState } from 'react';
import { JIRA_BASE_URL } from '../../utils/constants';
import { purgeJunkLogsApi } from '../../services/api';

export default function HistoryTable({
  history = [],
  loading,
  onDelete,
  onEscalate,
  onGenerateStarterLog = () => {},
}) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredHistory = (history || []).filter((log) => {
    const q = searchQuery.toLowerCase();
    return (
      !q ||
      (log.summary && log.summary.toLowerCase().includes(q)) ||
      (log.file_name && log.file_name.toLowerCase().includes(q)) ||
      (log.file_content && log.file_content.toLowerCase().includes(q))
    );
  });

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 border border-slate-800 rounded-xl bg-slate-950/40">
        Loading incident history logs...
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="p-10 text-center border border-slate-800 rounded-xl bg-slate-950/40 space-y-4">
        <div className="text-4xl">📋</div>
        <h3 className="text-sm font-bold text-slate-200">No Incident Logs Yet</h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
          Your incident history is empty. Head to the{' '}
          <span className="text-cyan-400 font-medium">Triage Console</span> tab to ingest your first log,
          or generate a starter log right now to explore the interface.
        </p>
        <button
          onClick={onGenerateStarterLog}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg shadow-lg shadow-cyan-950/40 transition-all"
        >
          ⚡ Generate Starter Log
        </button>
      </div>
    );
  }

  const handlePurgeJunk = async () => {
    if (!window.confirm('Purge all junk entries (short texts < 10 characters or greeting messages) from Incident History?')) return;
    try {
      const data = await purgeJunkLogsApi();
      alert(`🧹 ${data.detail || 'Junk logs purged successfully.'}`);
      onGenerateStarterLog(); // Triggers fetchHistory reload
    } catch (err) {
      console.error('Purge junk error:', err);
      alert('Failed to purge junk logs.');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <input
          type="text"
          placeholder="Filter history logs..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 w-64 focus:outline-none focus:border-cyan-500"
        />
        <button
          onClick={handlePurgeJunk}
          className="px-3 py-1.5 text-xs font-semibold bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800/60 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5"
          title="Bulk purge entries shorter than 10 characters or conversational greetings"
        >
          <span>🧹 Purge Junk Entries</span>
        </button>
      </div>

      <div className="overflow-x-auto border border-slate-800 rounded-xl bg-slate-950/50">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-900/80 text-xs uppercase text-slate-400 border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Jira Ticket</th>
              <th className="px-4 py-3">File / Source</th>
              <th className="px-4 py-3">Summary / Content Preview</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredHistory.map((log, index) => {
              const logId = log.id ?? log._id ?? log.log_id;
              const hasJira = log.jira_key && log.jira_key !== 'NOT_CREATED' && log.jira_key !== 'N/A';
              return (
                <tr key={logId || index} className="hover:bg-slate-900/40 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">
                    #{logId}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                        log.status === 'MANDATORY'
                          ? 'bg-amber-950 text-amber-400 border-amber-800/50'
                          : 'bg-cyan-950 text-cyan-400 border-cyan-800/50'
                      }`}
                    >
                      {log.status || 'Analyzed'}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {hasJira ? (
                      <a
                        href={`${JIRA_BASE_URL}/${log.jira_key}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 bg-indigo-950/80 hover:bg-indigo-900/90 text-indigo-300 border border-indigo-800/60 hover:border-indigo-600 px-2 py-0.5 rounded font-bold transition-colors hover:underline"
                        title={`Open ${log.jira_key} in Jira`}
                      >
                        🎟️ {log.jira_key}
                        <span className="text-[10px] opacity-70">↗</span>
                      </a>
                    ) : (
                      <span className="text-slate-600 text-[10px]">Unlinked</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">
                    {log.file_name || 'log_trace.log'}
                  </td>
                  <td className="px-4 py-3 text-slate-200 text-xs font-mono max-w-md truncate">
                    {log.summary || log.file_content || 'Log analysis record'}
                  </td>

                  <td className="px-4 py-3 text-right space-x-2">
                    {log.status === 'MANDATORY' || log.status === 'ESCALATED' ? (
                      <span className="inline-block px-2.5 py-1 text-xs font-medium bg-red-950/60 text-red-400 border border-red-800/60 rounded">
                        Escalated
                      </span>
                    ) : (
                      <button
                        onClick={() => onEscalate && onEscalate(logId)}
                        className="px-2.5 py-1 text-xs bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 border border-amber-800/60 rounded transition-colors"
                      >
                        Escalate
                      </button>
                    )}

                    <button
                      onClick={() => onDelete && onDelete(logId)}
                      className="px-2.5 py-1 text-xs bg-red-950/60 hover:bg-red-900/80 text-red-300 border border-red-800/60 rounded transition-colors"
                    >
                      Purge
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
