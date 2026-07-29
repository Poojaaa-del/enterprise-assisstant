// src/utils/auth.js

/**
 * Safely retrieve and validate stored JWT token from localStorage
 */
export const getStoredToken = () => {
  try {
    const rawToken = localStorage.getItem('token');
    if (
      !rawToken ||
      rawToken === 'null' ||
      rawToken === 'undefined' ||
      rawToken.trim() === ''
    ) {
      return null;
    }
    return rawToken;
  } catch {
    return null;
  }
};

/**
 * Store JWT token in localStorage
 */
export const setStoredToken = (token) => {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
};

/**
 * Remove JWT token from localStorage
 */
export const removeStoredToken = () => {
  localStorage.removeItem('token');
};

/**
 * Retrieve auth headers with Bearer token if present
 */
export const getAuthHeaders = () => {
  const token = getStoredToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

/**
 * Safely decode a JWT payload without an external library
 */
export const parseJwt = (token) => {
  try {
    if (!token) return null;
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};
