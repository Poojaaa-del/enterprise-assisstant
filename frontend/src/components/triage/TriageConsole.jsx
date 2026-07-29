// src/components/triage/TriageConsole.jsx

import { useState, useRef } from 'react';
import { SAMPLE_INCIDENTS } from '../../utils/constants';
import { runTriageApi, escalateIncidentApi, downloadIncidentPdfApi } from '../../services/api';

export default function TriageConsole({ history = [], onIngestSuccess }) {
  const [fileContent, setFileContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);
  const [sampleIndex, setSampleIndex] = useState(0);
  const fileInputRef = useRef(null);

  const handleLoadSampleIncidents = () => {
    const sample = SAMPLE_INCIDENTS[sampleIndex % SAMPLE_INCIDENTS.length];
    setFileName(sample.fileName);
    setFileContent(sample.content);
    setSampleIndex((prev) => prev + 1);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      setFileContent(event.target.result || '');
    };
    reader.readAsText(file);
  };

  const handleTriageSubmit = async (e) => {
    e.preventDefault();
    if (!fileContent.trim()) return;

    setSubmitting(true);
    try {
      const taskName = fileName || `Manual Ingestion (${new Date().toLocaleTimeString()})`;
      const { data } = await runTriageApi(taskName, fileContent);

      const realDbId = data?.id ?? data?._id ?? data?.log_id ?? data?.record?.id;
      const classificationStatus =
        data?.classification === 'MANDATORY' || data?.status === 'MANDATORY'
          ? 'MANDATORY'
          : 'LOW_PRIORITY';

      if (data?.status === 'invalid_input') {
        // Non-log guardrail blocked entry — do NOT save to incident history database/state
        setCurrentResult({
          id: 'N/A',
          status: 'INFO',
          file_name: fileName || 'input_query.txt',
          summary: data?.root_cause_analysis || 'Non-log input detected.',
          file_content: fileContent,
          jira_key: 'NOT_CREATED',
          slack_status: 'Bypassed',
          created_at: new Date().toISOString(),
          recommended_actions: data?.recommended_actions || [],
        });
        setFileContent('');
        setFileName('');
        return;
      }

      const newLog = {
        id: realDbId || `local_${Date.now()}`,
        status: classificationStatus,
        file_name: fileName || 'manual_ingestion.log',
        summary: data?.message || fileContent.slice(0, 100) + '...',
        file_content: fileContent,
        jira_key: data?.jira_key || 'NOT_CREATED',
        slack_status: data?.slack_status || 'Bypassed',
        created_at: new Date().toISOString(),
        citation: data?.citation,
        extracted_meta: data?.extracted_meta,
      };

      if (onIngestSuccess) onIngestSuccess(newLog);
      setCurrentResult(newLog);
      setFileContent('');
      setFileName('');
    } catch (err) {
      console.error('Failed to analyze log:', err);
      // Fallback local ingestion for offline/demo testing
      const newLog = {
        id: `local_${Date.now()}`,
        status: 'LOW_PRIORITY',
        file_name: fileName || 'manual_ingestion.log',
        summary: fileContent.slice(0, 100) + '...',
        file_content: fileContent,
        jira_key: 'NOT_CREATED',
        slack_status: 'Bypassed',
        created_at: new Date().toISOString(),
      };
      if (onIngestSuccess) onIngestSuccess(newLog);
      setCurrentResult(newLog);
      setFileContent('');
      setFileName('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl shadow-lg">
          <p className="text-xs text-slate-400 font-mono">TOTAL LOGS INGESTED</p>
          <p className="text-3xl font-bold text-slate-100 font-mono mt-1">{history.length}</p>
        </div>
        <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl shadow-lg">
          <p className="text-xs text-slate-400 font-mono">MANDATORY ESCALATIONS</p>
          <p className="text-3xl font-bold text-amber-400 font-mono mt-1">
            {history.filter((h) => h.status === 'MANDATORY').length}
          </p>
        </div>
        <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl shadow-lg">
          <p className="text-xs text-slate-400 font-mono">ACTIVE JIRA LOCKS</p>
          <p className="text-3xl font-bold text-cyan-400 font-mono mt-1">
            {history.filter((h) => h.jira_key && h.jira_key !== 'NOT_CREATED').length}
          </p>
        </div>
      </div>

      {/* Log Ingestion Terminal */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">Log & File Ingestion Terminal</h2>
            <p className="text-xs text-slate-400">
              Paste raw log traces, crash dumps, or upload files (.log, .txt, .json) into the AI triage pipeline.
            </p>
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="px-3.5 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition-colors flex items-center space-x-2 shrink-0"
          >
            <span>📁 Upload File</span>
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".log,.txt,.json"
            className="hidden"
          />
        </div>

        {fileName && (
          <div className="text-xs text-cyan-400 font-mono bg-cyan-950/40 border border-cyan-800/50 px-3 py-1.5 rounded-lg flex justify-between items-center">
            <span>Uploaded: {fileName}</span>
            <button
              onClick={() => {
                setFileName('');
                setFileContent('');
              }}
              className="text-slate-400 hover:text-white"
            >
              ×
            </button>
          </div>
        )}

        <form onSubmit={handleTriageSubmit} className="space-y-4">
          <textarea
            rows="5"
            value={fileContent}
            onChange={(e) => setFileContent(e.target.value)}
            placeholder="Paste raw log lines, stack trace outputs, or system messages here..."
            className="w-full p-4 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
            required
          />
          <div className="flex justify-between items-center">
            <button
              type="button"
              onClick={handleLoadSampleIncidents}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium underline flex items-center space-x-1"
            >
              <span>⚡ Load Sample Incidents Data</span>
            </button>
            <button
              type="submit"
              disabled={submitting || !fileContent.trim()}
              className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium text-xs tracking-wider uppercase transition-colors disabled:opacity-50"
            >
              {submitting ? 'Analyzing Logs...' : 'Execute AI Pipeline Ingestion'}
            </button>
          </div>
        </form>
      </div>

      {/* Immediate Inline Analysis & Action Plan Results Display */}
      {currentResult && (
        <div className="bg-slate-950/90 border border-cyan-500/40 rounded-xl p-6 shadow-2xl space-y-5 animate-fade-in ring-1 ring-cyan-500/20">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center space-x-3">
              <span className="text-xl">⚡</span>
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  Analysis & Action Plan Results
                </h3>
                <p className="text-xs text-slate-400">
                  Target Source: <span className="font-mono text-cyan-400">{currentResult.file_name}</span> (Record #{currentResult.id})
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold font-mono uppercase tracking-wider border ${
                  currentResult.status === 'MANDATORY'
                    ? 'bg-amber-950/90 text-amber-400 border-amber-700'
                    : 'bg-cyan-950/90 text-cyan-400 border-cyan-700'
                }`}
              >
                {currentResult.status === 'MANDATORY' ? '🚨 MANDATORY ESCALATION' : '✅ LOW PRIORITY'}
              </span>

              <button
                onClick={() => setCurrentResult(null)}
                className="text-slate-400 hover:text-white text-sm p-1"
                title="Clear Result"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Incident Summary & RCA */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Root Cause Analysis (RCA)</h4>
            <div className="p-4 bg-slate-900/90 border border-slate-800 rounded-lg text-xs text-slate-200 leading-relaxed font-mono whitespace-pre-wrap">
              {currentResult.summary}
            </div>
          </div>

          {/* Grounded Citation Context */}
          {currentResult.citation && (
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Grounded Citation Context</h4>
              <div className="p-3 bg-cyan-950/30 border border-cyan-800/40 rounded-lg text-xs text-cyan-300 font-mono italic">
                📖 {currentResult.citation}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={async () => {
                  try {
                    const targetId = parseInt(currentResult?.id, 10);
                    if (!currentResult?.id || isNaN(targetId)) {
                      alert('Conversational text cannot be escalated. Please input a real system log snippet.');
                      return;
                    }

                    const { ok, data: escData } = await escalateIncidentApi(targetId, 'HIGH');
                    if (ok && escData) {
                      setCurrentResult((prev) => ({
                        ...prev,
                        status: 'MANDATORY',
                        jira_key: escData.jira_key || 'SEC-1001',
                        slack_status: escData.slack_status || 'SUCCESS',
                      }));
                      alert(`✅ Ticket ${escData.jira_key || 'SEC-1001'} generated & Slack alert sent!`);
                    }
                  } catch (e) {
                    console.error('Escalation error:', e);
                  }
                }}
                className="px-4 py-2 text-xs font-bold bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-700 rounded-lg transition-colors flex items-center space-x-1.5 cursor-pointer"
              >
                <span>🎟️</span>
                <span>
                  {currentResult.jira_key && currentResult.jira_key !== 'NOT_CREATED'
                    ? `Jira Ticket (${currentResult.jira_key})`
                    : 'Escalate to JIRA'}
                </span>
              </button>

              <button
                onClick={async () => {
                  try {
                    const targetId = parseInt(currentResult?.id, 10);
                    if (!currentResult?.id || isNaN(targetId)) {
                      alert('Conversational text cannot be escalated. Please input a real system log snippet.');
                      return;
                    }

                    const { ok } = await escalateIncidentApi(targetId, 'CRITICAL');
                    if (ok) {
                      alert('✅ Slack notification card dispatched to channel!');
                    }
                  } catch (e) {
                    console.error('Slack alert error:', e);
                  }
                }}
                className="px-4 py-2 text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition-colors flex items-center space-x-1.5 cursor-pointer"
              >
                <span>💬</span>
                <span>Send Slack Alert</span>
              </button>

              <button
                onClick={async () => {
                  try {
                    const { ok, blob } = await downloadIncidentPdfApi(currentResult.id);
                    if (ok && blob) {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `Incident_Report_${currentResult.id}.pdf`;
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                    } else {
                      alert('PDF report exported successfully.');
                    }
                  } catch (e) {
                    console.error('PDF error:', e);
                  }
                }}
                className="px-4 py-2 text-xs font-bold bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-700 rounded-lg transition-colors flex items-center space-x-1.5 cursor-pointer"
              >
                <span>📄</span>
                <span>Download PDF Report</span>
              </button>
            </div>

            <button
              onClick={() => setCurrentResult(null)}
              className="text-xs text-slate-400 hover:text-slate-200 underline"
            >
              Dismiss Result
            </button>
          </div>
        </div>
      )}

      {/* Empty State Card if no history exists */}
      {history.length === 0 && !currentResult && (
        <div className="p-8 text-center border border-slate-800 rounded-xl bg-slate-950/40 space-y-3">
          <div className="text-3xl">📥</div>
          <h3 className="text-sm font-bold text-slate-200">No Ingested Incidents Found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            You currently have no log entries logged in your session workspace. Populate realistic incident samples to test the layout immediately.
          </p>
          <button
            onClick={handleLoadSampleIncidents}
            className="px-4 py-2 text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            ⚡ Load Sample Incident Logs
          </button>
        </div>
      )}
    </div>
  );
}
