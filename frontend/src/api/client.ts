/// <reference types="vite/client" />

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// --- Token Management Helpers ---
export const TOKEN_KEY = 'guardcore_jwt_token';

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token);
export const removeToken = (): void => localStorage.removeItem(TOKEN_KEY);

// --- Base HTTP Fetch Wrapper ---
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Session expired or invalid token: clean up local storage
    removeToken();
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

// --- Auth Endpoints ---
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    username: string;
    full_name?: string;
  };
}

export const authApi = {
  login: async (credentials: { username_or_email: string; password: string }): Promise<AuthResponse> => {
    const data = await apiFetch<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    if (data.access_token) {
      setToken(data.access_token);
    }
    return data;
  },

  signup: async (userData: { email: string; username: string; password: string; full_name?: string }) => {
    return apiFetch('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  getCurrentUser: async () => {
    return apiFetch('/auth/me');
  },

  logout: () => {
    removeToken();
  },
};

// --- Triage Endpoints ---
export const triageApi = {
  getHistory: async () => {
    return apiFetch('/history');
  },

  submitTriage: async (payload: { task_name: string; context: { emails: string[]; local_files: string[] } }) => {
    return apiFetch('/triage', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  escalateLog: async (logId: number) => {
    return apiFetch(`/logs/${logId}/escalate`, {
      method: 'POST',
    });
  },

  deleteLog: async (logId: number) => {
    return apiFetch(`/logs/${logId}`, {
      method: 'DELETE',
    });
  },
};