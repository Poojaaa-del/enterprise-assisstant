// src/api.js
import { API_BASE } from './utils/constants';

const BASE_URL = `${API_BASE}/api/v1`;

/**
 * Helper to fetch stored JWT and attach Authorization header
 */
const getAuthHeaders = () => {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

/**
 * Log in to retrieve JWT access token
 */
export const login = async (username = "admin", password = "password123") => {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Authentication failed. Please check credentials.");
  }

  const data = await response.json();
  localStorage.setItem("token", data.access_token);
  return data;
};

/**
 * Protected: Trigger Triage Pipeline
 */
export const runTriage = async (taskName, incidentText) => {
  const response = await fetch(`${BASE_URL}/triage`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      task_name: taskName,
      context: {
        emails: [],
        local_files: [incidentText],
      },
    }),
  });

  if (!response.ok) {
    if (response.status === 401) throw new Error("Unauthorized! Please log in.");
    throw new Error("Failed to process triage stream.");
  }

  return await response.json();
};

/**
 * Unprotected: Fetch historical compliance logs
 */
export const fetchHistory = async () => {
  const response = await fetch(`${BASE_URL}/history`);
  if (!response.ok) throw new Error("Failed to fetch logs.");
  return await response.json();
};

/**
 * Protected: Force escalate a log entry
 */
export const escalateLog = async (logId) => {
  const response = await fetch(`${BASE_URL}/logs/${logId}/escalate`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) throw new Error("Failed to escalate log.");
  return await response.json();
};

/**
 * Protected: Permanently purge a log entry
 */
export const purgeLog = async (logId) => {
  const response = await fetch(`${BASE_URL}/logs/${logId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) throw new Error("Failed to purge log.");
  return await response.json();
};