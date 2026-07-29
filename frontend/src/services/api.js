// src/services/api.js

import { API_BASE } from '../utils/constants';
import { getAuthHeaders, getStoredToken } from '../utils/auth';

/**
 * Extract error message safely from API response payloads
 */
export const extractErrorMessage = (data, defaultMessage = 'API Request Failed') => {
  if (!data) return defaultMessage;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail) && data.detail.length > 0) {
    const first = data.detail[0];
    if (typeof first === 'string') return first;
    if (first && typeof first.msg === 'string') return first.msg;
  }
  if (data.message && typeof data.message === 'string') return data.message;
  return defaultMessage;
};

/* ==========================================================================
   AUTHENTICATION API
   ========================================================================== */

export const loginApi = async (username, email, password) => {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  if (!res.ok) {
    const errMsg = extractErrorMessage(data, `Authentication failed with status ${res.status}`);
    throw new Error(errMsg);
  }

  return data;
};

export const signupApi = async (username, email, password) => {
  const res = await fetch(`${API_BASE}/api/v1/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  if (!res.ok) {
    const errMsg = extractErrorMessage(data, `Signup failed with status ${res.status}`);
    throw new Error(errMsg);
  }

  return data;
};

export const verifyEmailApi = async (token) => {
  const res = await fetch(`${API_BASE}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`);

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  if (!res.ok) {
    const errMsg = extractErrorMessage(data, `Email verification failed with status ${res.status}`);
    throw new Error(errMsg);
  }

  return data;
};

export const googleAuthApi = async (token) => {
  const res = await fetch(`${API_BASE}/api/v1/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  if (!res.ok) {
    throw new Error(data?.detail || `Google authentication failed with status ${res.status}`);
  }

  if (!data?.access_token) {
    throw new Error('Invalid server response: Access token missing.');
  }

  return data;
};

/* ==========================================================================
   INCIDENT & LOG HISTORY API
   ========================================================================== */

export const fetchHistoryApi = async () => {
  let res = await fetch(`${API_BASE}/api/v1/history`, {
    headers: getAuthHeaders(),
  });

  if (res.status === 404) {
    res = await fetch(`${API_BASE}/api/v1/logs`, {
      headers: getAuthHeaders(),
    });
  }

  if (res.status === 401) {
    return { status: 401, data: [] };
  }

  if (!res.ok) {
    return { status: res.status, data: [] };
  }

  const data = await res.json();
  const parsed = Array.isArray(data)
    ? data
    : Array.isArray(data?.logs)
    ? data.logs
    : Array.isArray(data?.records)
    ? data.records
    : Array.isArray(data?.items)
    ? data.items
    : [];

  return { status: 200, data: parsed };
};

export const deleteLogApi = async (logId) => {
  const res = await fetch(`${API_BASE}/api/v1/logs/${logId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  if (res.status === 401) {
    return { status: 401 };
  }
  return { status: res.status, ok: res.ok };
};

export const purgeJunkLogsApi = async () => {
  const res = await fetch(`${API_BASE}/api/v1/logs/purge-junk`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Purge junk logs failed with status ${res.status}`);
  }
  return await res.json();
};

export const escalateIncidentApi = async (incidentId, severity = 'HIGH') => {
  const res = await fetch(`${API_BASE}/api/v1/incidents/escalate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ incident_id: incidentId, severity }),
  });

  if (res.status === 401) {
    return { status: 401, ok: false };
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  return { status: res.status, ok: res.ok, data };
};

/* ==========================================================================
   TRIAGE PIPELINE API
   ========================================================================== */

export const runTriageApi = async (taskName, fileContent) => {
  const payload = {
    task_name: taskName,
    context: { emails: [], local_files: [fileContent] },
  };

  const res = await fetch(`${API_BASE}/api/v1/triage`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  return { status: res.status, ok: res.ok, data };
};

/* ==========================================================================
   KNOWLEDGE BASE & RAG AGENT API
   ========================================================================== */

export const fetchKnowledgeArticlesApi = async () => {
  const res = await fetch(`${API_BASE}/api/v1/knowledge/articles`, {
    headers: getAuthHeaders(),
  });

  if (res.status === 401) {
    return { status: 401, data: [] };
  }

  if (!res.ok) {
    return { status: res.status, data: [] };
  }

  const data = await res.json();
  if (data.status === 'SUCCESS') {
    return { status: 200, data: data.articles || data.files || [] };
  }
  return { status: 200, data: Array.isArray(data) ? data : [] };
};

export const fetchKnowledgeFilesApi = async () => {
  const res = await fetch(`${API_BASE}/api/v1/knowledge/files`, {
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    return { status: res.status, data: [] };
  }

  let raw = null;
  try {
    raw = await res.json();
  } catch {
    return { status: 200, data: [] };
  }

  // Safely extract the files array from any response shape:
  // • { status: "SUCCESS", files: [...] }  — backend wrapped format
  // • { files: [...] }                      — simplified wrapped format
  // • [...]                                 — bare array (future-proof)
  const files = Array.isArray(raw)
    ? raw
    : Array.isArray(raw?.files)
    ? raw.files
    : Array.isArray(raw?.data)
    ? raw.data
    : [];

  return { status: 200, data: files };
};

export const uploadKnowledgeFilesApi = async (filesList) => {
  const formData = new FormData();
  Array.from(filesList).forEach((file) => {
    formData.append('files', file);
  });

  const token = getStoredToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const res = await fetch(`${API_BASE}/api/v1/knowledge/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  // Parse body regardless of status so callers always receive structured data
  let data = null;
  try {
    data = await res.json();
  } catch {
    // body parsing fallback
  }

  // 202 Accepted = background processing queued — treat as success
  if (!res.ok && res.status !== 202) {
    const errMsg = extractErrorMessage(data, `File upload failed with status ${res.status}`);
    throw new Error(errMsg);
  }

  return { ok: true, status: res.status, data };
};

export const deleteKnowledgeFileApi = async (fileId) => {
  const res = await fetch(`${API_BASE}/api/v1/knowledge/files/${fileId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  return { status: res.status, ok: res.ok };
};

export const createKnowledgeArticleApi = async (article) => {
  const res = await fetch(`${API_BASE}/api/v1/knowledge/articles`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(article),
  });

  return { status: res.status, ok: res.ok };
};

export const ingestSampleArticlesApi = async (articles) => {
  for (const article of articles) {
    await fetch(`${API_BASE}/api/v1/knowledge/articles`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(article),
    });
  }
};

export const deleteKnowledgeArticleApi = async (articleId) => {
  const res = await fetch(`${API_BASE}/api/v1/knowledge/articles/${articleId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  return { status: res.status, ok: res.ok };
};

export const runAgentQueryApi = async (question) => {
  try {
    const res = await fetch(`${API_BASE}/api/v1/knowledge/agent-query`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ question }),
    });

    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
  } catch {
    // Fallthrough to single-pass fallback
  }

  // Fallback query endpoint
  const fallbackRes = await fetch(`${API_BASE}/api/v1/knowledge/query`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ question }),
  });

  const fallbackData = await fallbackRes.json();
  return { ok: false, data: fallbackData };
};

/* ==========================================================================
   USER ACCOUNT MANAGEMENT API
   ========================================================================== */

export const deleteUserAccount = async () => {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // response body parsing fallback
  }

  if (!res.ok) {
    const errMsg = extractErrorMessage(data, `Account deletion failed with status ${res.status}`);
    throw new Error(errMsg);
  }

  return data;
};

/* ==========================================================================
   REPORT & PDF GENERATION API
   ========================================================================== */

export const exportPdfReportApi = async (query, answer, citations, confidence) => {
  const res = await fetch(`${API_BASE}/api/v1/reports/export-pdf`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      query: query || 'Enterprise Query',
      answer,
      citations: citations || [],
      confidence: confidence || 0,
    }),
  });

  if (!res.ok) {
    throw new Error(`PDF export endpoint returned status ${res.status}`);
  }

  return await res.blob();
};

export const downloadIncidentPdfApi = async (logId) => {
  const res = await fetch(`${API_BASE}/api/v1/reports/pdf/${logId}`, {
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    return { ok: false };
  }

  const blob = await res.blob();
  return { ok: true, blob };
};
