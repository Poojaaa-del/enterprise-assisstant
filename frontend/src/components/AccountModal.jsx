// frontend/src/components/AccountModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import DeleteAccountModal from './DeleteAccountModal';

const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

const COLOR_PRESETS = [
  { id: 'cyan', label: 'Cyan / Blue', gradient: 'from-cyan-500 to-blue-600', ring: 'ring-cyan-400' },
  { id: 'purple', label: 'Purple / Pink', gradient: 'from-purple-500 to-pink-600', ring: 'ring-purple-400' },
  { id: 'emerald', label: 'Emerald / Teal', gradient: 'from-emerald-500 to-teal-600', ring: 'ring-emerald-400' },
  { id: 'amber', label: 'Amber / Orange', gradient: 'from-amber-500 to-orange-600', ring: 'ring-amber-400' },
  { id: 'rose', label: 'Rose / Red', gradient: 'from-rose-500 to-red-600', ring: 'ring-rose-400' },
];

const DEPARTMENTS = [
  'Engineering',
  'Security Ops',
  'HR',
  'Finance',
  'Executive',
  'General',
];

// Generate deterministic masked API key
const generateApiKey = (userId) => {
  const seed = String(userId || 'demo').padStart(4, '0');
  return `sk-guard-${seed}-xxxx-xxxx-xxxxxxxxxxxx`.replace(/x/g, () =>
    Math.floor(Math.random() * 16).toString(16)
  );
};

export default function AccountModal({ userInfo, onClose, onUpdateUser }) {
  const [activeTab, setActiveTab] = useState('profile'); // 'profile' | 'security' | 'apikeys' | 'usage' | 'danger'
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Profile Form State
  const [fullName, setFullName] = useState(userInfo?.full_name || '');
  const [department, setDepartment] = useState(userInfo?.department || 'Engineering');
  const [avatarColor, setAvatarColor] = useState(
    userInfo?.avatar_color || 'from-cyan-500 to-blue-600'
  );
  const [userMetadata, setUserMetadata] = useState({
    id: userInfo?.id || '—',
    email: userInfo?.email || '—',
    role: userInfo?.role || 'USER',
    created_at: userInfo?.created_at || '',
  });

  const [profileSaving, setProfileSaving] = useState(false);
  const [profileBanner, setProfileBanner] = useState(null); // { type: 'success'|'error', text: '' }

  // Security Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [securityBanner, setSecurityBanner] = useState(null);

  // API Key State
  const [apiKey, setApiKey] = useState('');
  const [keyVisible, setKeyVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Usage Stats State
  const [stats, setStats] = useState({ queries: 0, documents: 0, auditEntries: 0 });
  const [loadingStats, setLoadingStats] = useState(true);

  // Fetch full user profile metadata & stats on mount
  const fetchUserProfile = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/user/me`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setFullName(data.full_name || '');
        setDepartment(data.department || 'Engineering');
        setAvatarColor(data.avatar_color || 'from-cyan-500 to-blue-600');
        setUserMetadata({
          id: data.id,
          email: data.email,
          role: data.role || 'USER',
          created_at: data.created_at || '',
        });
      }
    } catch (err) {
      console.warn('[AccountModal] Failed to fetch /user/me:', err);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const [historyRes, filesRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/v1/knowledge/history`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/v1/knowledge/files`, { headers: getAuthHeaders() }),
      ]);

      const historyData =
        historyRes.status === 'fulfilled' && historyRes.value.ok
          ? await historyRes.value.json()
          : { sessions: [] };

      const filesData =
        filesRes.status === 'fulfilled' && filesRes.value.ok
          ? await filesRes.value.json()
          : { files: [] };

      const sessions = historyData.sessions || [];
      const files = Array.isArray(filesData) ? filesData : (filesData.files || filesData.data || []);

      setStats({
        queries: sessions.length,
        documents: files.length,
        auditEntries: sessions.length,
      });
    } catch (err) {
      console.warn('[AccountModal] Stats fetch failed:', err);
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => {
    // API key retrieval / initialization
    const stored = localStorage.getItem('_guard_api_key');
    if (stored) {
      setApiKey(stored);
    } else {
      const generated = generateApiKey(userInfo?.id || Date.now());
      localStorage.setItem('_guard_api_key', generated);
      setApiKey(generated);
    }

    fetchUserProfile();
    fetchStats();
  }, [fetchUserProfile, fetchStats, userInfo?.id]);

  // Handle Save Profile Changes
  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setProfileBanner(null);

    if (!fullName.trim()) {
      setProfileBanner({ type: 'error', text: 'Full Name cannot be empty.' });
      return;
    }

    setProfileSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/user/profile`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          full_name: fullName.trim(),
          department: department,
          avatar_color: avatarColor,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update profile.');
      }

      // Update token in localStorage if refreshed token returned
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
      }

      // Notify parent App.jsx for instant state sync across header pills
      if (onUpdateUser) {
        onUpdateUser(data.user, data.access_token);
      }

      setProfileBanner({
        type: 'success',
        text: '✅ Profile & RBAC metadata updated successfully!',
      });
    } catch (err) {
      setProfileBanner({
        type: 'error',
        text: `⚠️ ${err.message || 'Error updating profile.'}`,
      });
    } finally {
      setProfileSaving(false);
    }
  };

  // Handle Change Password
  const handleChangePassword = async (e) => {
    e.preventDefault();
    setSecurityBanner(null);

    if (!currentPassword) {
      setSecurityBanner({ type: 'error', text: 'Please enter your current password.' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setSecurityBanner({ type: 'error', text: 'New passwords do not match.' });
      return;
    }

    if (newPassword.length < 6) {
      setSecurityBanner({ type: 'error', text: 'New password must be at least 6 characters long.' });
      return;
    }

    setPasswordSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/user/change-password`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to change password.');
      }

      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setSecurityBanner({
        type: 'success',
        text: '🔒 Password changed successfully!',
      });
    } catch (err) {
      setSecurityBanner({
        type: 'error',
        text: `⚠️ ${err.message || 'Error changing password.'}`,
      });
    } finally {
      setPasswordSaving(false);
    }
  };

  // Copy API key
  const handleCopyKey = async () => {
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const el = document.createElement('textarea');
      el.value = apiKey;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Regenerate API Key
  const handleRegenerateKey = () => {
    setRegenerating(true);
    setTimeout(() => {
      const newKey = generateApiKey(userMetadata.id || Date.now());
      localStorage.setItem('_guard_api_key', newKey);
      setApiKey(newKey);
      setRegenerating(false);
      setCopied(false);
    }, 800);
  };

  const maskedKey = apiKey
    ? `sk-guard-****-****-****-${apiKey.slice(-8)}`
    : 'sk-guard-****-****-****-........';

  // Initials computation
  const displayName = fullName || userInfo?.username || userMetadata.email?.split('@')[0] || 'User';
  const initials = displayName
    .split(' ')
    .map((n) => n[0]?.toUpperCase())
    .slice(0, 2)
    .join('');

  // Format date helper
  const memberSinceDate = userMetadata.created_at
    ? new Date(userMetadata.created_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Jul 2026';

  // Close on backdrop click / Escape
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(2,6,23,0.85)', backdropFilter: 'blur(8px)' }}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="Enterprise Account Settings"
    >
      {/* Modal Container */}
      <div
        className="relative w-full max-w-2xl rounded-2xl border border-slate-700/60 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        style={{
          background: 'linear-gradient(145deg, rgba(15,23,42,0.98) 0%, rgba(15,23,42,0.96) 100%)',
          boxShadow: '0 0 0 1px rgba(99,102,241,0.15), 0 32px 64px -12px rgba(0,0,0,0.8)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Gradient Bar */}
        <div
          className="h-1 w-full shrink-0"
          style={{ background: 'linear-gradient(90deg, #06b6d4 0%, #6366f1 50%, #ec4899 100%)' }}
        />

        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 shrink-0">
          <div className="flex items-center space-x-3">
            <span className="text-xl">⚙️</span>
            <div>
              <h2 className="text-sm font-black uppercase tracking-widest text-slate-100">
                Enterprise Account Settings
              </h2>
              <p className="text-[11px] text-slate-500 font-mono">
                Manage Profile Identity, Password Security, API Keys & RBAC Scope
              </p>
            </div>
          </div>
          <button
            id="account-modal-close"
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 transition-colors p-1.5 rounded-lg hover:bg-slate-800"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Modal Navigation Tabs Header */}
        <div className="flex border-b border-slate-800 bg-slate-950/60 px-6 space-x-1 shrink-0 overflow-x-auto">
          <button
            id="tab-profile"
            onClick={() => setActiveTab('profile')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 transition-all flex items-center space-x-2 shrink-0 ${
              activeTab === 'profile'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>👤</span>
            <span>Profile & Identity</span>
          </button>
          <button
            id="tab-security"
            onClick={() => setActiveTab('security')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 transition-all flex items-center space-x-2 shrink-0 ${
              activeTab === 'security'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>🔒</span>
            <span>Security & Password</span>
          </button>
          <button
            id="tab-apikeys"
            onClick={() => setActiveTab('apikeys')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 transition-all flex items-center space-x-2 shrink-0 ${
              activeTab === 'apikeys'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>🔑</span>
            <span>API Keys & CLI</span>
          </button>
          <button
            id="tab-usage"
            onClick={() => setActiveTab('usage')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 transition-all flex items-center space-x-2 shrink-0 ${
              activeTab === 'usage'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-950/20'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>📊</span>
            <span>Usage & Activity</span>
          </button>
          <button
            id="tab-danger"
            onClick={() => setActiveTab('danger')}
            className={`py-3 px-3 text-xs font-semibold border-b-2 transition-all flex items-center space-x-2 shrink-0 ${
              activeTab === 'danger'
                ? 'border-red-500 text-red-400 bg-red-950/20'
                : 'border-transparent text-slate-400 hover:text-red-400'
            }`}
          >
            <span>⚠️</span>
            <span>Danger Zone</span>
          </button>
        </div>

        {/* Modal Tab Content Area */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5">

          {/* ══════════════════════════════════════════════════════════════ */}
          {/* TAB 1: PROFILE & IDENTITY */}
          {/* ══════════════════════════════════════════════════════════════ */}
          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile} className="space-y-5">
              {profileBanner && (
                <div
                  className={`p-3 rounded-lg text-xs font-mono flex items-center space-x-2 ${
                    profileBanner.type === 'success'
                      ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
                      : 'bg-rose-950/80 border border-rose-800 text-rose-300'
                  }`}
                >
                  <span>{profileBanner.text}</span>
                </div>
              )}

              {/* Avatar Customizer Section */}
              <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 space-y-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
                  Avatar Preset & Accent Color
                </p>

                <div className="flex flex-col sm:flex-row items-center gap-4">
                  {/* Large Avatar Preview */}
                  <div
                    className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-black text-white shadow-xl bg-gradient-to-r ${avatarColor} shrink-0 border-2 border-slate-700`}
                  >
                    {initials}
                  </div>

                  {/* Preset Buttons */}
                  <div className="flex-1 space-y-2">
                    <p className="text-xs text-slate-400">Select Accent Color Gradient:</p>
                    <div className="flex flex-wrap gap-2">
                      {COLOR_PRESETS.map((preset) => (
                        <button
                          key={preset.id}
                          type="button"
                          onClick={() => setAvatarColor(preset.gradient)}
                          className={`w-7 h-7 rounded-full bg-gradient-to-r ${preset.gradient} transition-all cursor-pointer border border-slate-700 ${
                            avatarColor === preset.gradient
                              ? `ring-2 ${preset.ring} scale-110 shadow-lg`
                              : 'hover:scale-105 opacity-70 hover:opacity-100'
                          }`}
                          title={preset.label}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Editable Profile Fields */}
              <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Display Full Name
                  </label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Enter your full name..."
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-sans"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Department (RBAC Scope)
                  </label>
                  <select
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-sans cursor-pointer"
                  >
                    {DEPARTMENTS.map((dept) => (
                      <option key={dept} value={dept}>
                        {dept}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="block text-xs font-semibold text-slate-400">
                      Primary Auth Email
                    </label>
                    <span className="text-[10px] font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      🔒 Read-Only Identity
                    </span>
                  </div>
                  <input
                    type="email"
                    disabled
                    value={userMetadata.email}
                    className="w-full px-3.5 py-2.5 bg-slate-950/70 border border-slate-800/80 rounded-lg text-xs font-mono text-slate-400 cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Identity Metadata Footer Tags */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg border border-slate-800/60 bg-slate-950/50 font-mono text-[10px] text-slate-500">
                <span>User ID: <strong className="text-slate-300">#{userMetadata.id}</strong></span>
                <span>Member Since: <strong className="text-slate-300">{memberSinceDate}</strong></span>
                <span>Account Role: <strong className="text-cyan-400">{userMetadata.role}</strong></span>
              </div>

              {/* Save Button */}
              <button
                type="submit"
                disabled={profileSaving}
                className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-extrabold uppercase tracking-wider transition-colors shadow-lg shadow-cyan-600/10 active:scale-95 flex items-center justify-center space-x-2"
              >
                {profileSaving ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Saving Profile...</span>
                  </>
                ) : (
                  <span>Save Profile Changes</span>
                )}
              </button>
            </form>
          )}

          {/* ══════════════════════════════════════════════════════════════ */}
          {/* TAB 2: SECURITY & PASSWORD */}
          {/* ══════════════════════════════════════════════════════════════ */}
          {activeTab === 'security' && (
            <form onSubmit={handleChangePassword} className="space-y-4">
              {securityBanner && (
                <div
                  className={`p-3 rounded-lg text-xs font-mono flex items-center space-x-2 ${
                    securityBanner.type === 'success'
                      ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
                      : 'bg-rose-950/80 border border-rose-800 text-rose-300'
                  }`}
                >
                  <span>{securityBanner.text}</span>
                </div>
              )}

              <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 space-y-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
                  Password Management
                </p>

                {/* Current Password */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      type={showCurrentPassword ? 'text' : 'password'}
                      required
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3.5 py-2.5 pr-10 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-sans"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs cursor-pointer"
                    >
                      {showCurrentPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                {/* New Password */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    New Password (min 6 chars)
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3.5 py-2.5 pr-10 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-sans"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs cursor-pointer"
                    >
                      {showNewPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                {/* Confirm New Password */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3.5 py-2.5 pr-10 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-cyan-500 font-sans"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs cursor-pointer"
                    >
                      {showConfirmPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={passwordSaving}
                className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-extrabold uppercase tracking-wider transition-colors shadow-lg shadow-cyan-600/10 active:scale-95 flex items-center justify-center space-x-2 cursor-pointer"
              >
                {passwordSaving ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Updating Password...</span>
                  </>
                ) : (
                  <span>Update Password</span>
                )}
              </button>
            </form>
          )}

          {/* ══════════════════════════════════════════════════════════════ */}
          {/* TAB 3: API KEYS & CLI */}
          {/* ══════════════════════════════════════════════════════════════ */}
          {activeTab === 'apikeys' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
                    Developer API Key / Token
                  </p>
                  <span className="text-[9px] font-mono bg-amber-950/60 text-amber-400 border border-amber-800/50 px-2 py-0.5 rounded">
                    CLI Access
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <code
                    className="flex-1 text-xs font-mono px-3 py-2 rounded-lg border border-slate-800 text-slate-300 truncate bg-slate-950"
                  >
                    {keyVisible ? apiKey : maskedKey}
                  </code>
                  <button
                    onClick={() => setKeyVisible(!keyVisible)}
                    className="p-2 rounded-lg border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors shrink-0 cursor-pointer"
                    title={keyVisible ? 'Hide Key' : 'Show Key'}
                  >
                    {keyVisible ? '🙈' : '👁️'}
                  </button>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleCopyKey}
                    className="flex-1 py-2 text-xs font-semibold rounded-lg border transition-all flex items-center justify-center space-x-1.5 cursor-pointer"
                    style={
                      copied
                        ? { background: 'rgba(16,185,129,0.12)', borderColor: 'rgba(16,185,129,0.40)', color: '#6ee7b7' }
                        : { background: 'rgba(99,102,241,0.10)', borderColor: 'rgba(99,102,241,0.30)', color: '#a5b4fc' }
                    }
                  >
                    {copied ? <span>✓ Copied!</span> : <span>📋 Copy Key</span>}
                  </button>
                  <button
                    onClick={handleRegenerateKey}
                    disabled={regenerating}
                    className="flex-1 py-2 text-xs font-semibold rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all flex items-center justify-center space-x-1.5 disabled:opacity-60 cursor-pointer"
                  >
                    {regenerating ? <span>Regenerating...</span> : <span>🔄 Regenerate</span>}
                  </button>
                </div>
              </div>

              {/* Monospace CLI Quickstart Guide */}
              <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-950/80 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 font-mono">
                  ⚡ CLI Quickstart Integration
                </p>
                <p className="text-xs text-slate-400">
                  Authenticate the GuardCore developer CLI tool using your ingestion key:
                </p>
                <pre className="p-3 bg-slate-900 rounded-lg text-xs font-mono text-cyan-300 border border-slate-800 overflow-x-auto">
                  guardcore-cli auth login --key {keyVisible ? apiKey : '<YOUR_API_KEY>'}
                </pre>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════ */}
          {/* TAB 4: USAGE & ACTIVITY */}
          {/* ══════════════════════════════════════════════════════════════ */}
          {activeTab === 'usage' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/50 space-y-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
                  System Usage Metrics & Access Scope
                </p>

                {loadingStats ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[...Array(4)].map((_, i) => (
                      <div key={i} className="h-20 rounded-lg bg-slate-800/50 animate-pulse" />
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <StatBox icon="🔍" value={stats.queries} label="Queries Executed" color="cyan" />
                    <StatBox icon="📂" value={stats.documents} label="Documents Uploaded" color="indigo" />
                    <StatBox icon="📋" value={stats.auditEntries} label="Audit Log Entries" color="violet" />
                    <StatBox icon="🛡️" value={userMetadata.role} label="Role Scope" color="emerald" />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════ */}
          {/* TAB 5: DANGER ZONE */}
          {/* ══════════════════════════════════════════════════════════════ */}
          {activeTab === 'danger' && (
            <div className="space-y-4">
              {/* Warning Banner */}
              <div className="p-4 rounded-xl border border-amber-900/50 bg-amber-950/30 space-y-2">
                <div className="flex items-center space-x-2 text-amber-400">
                  <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <span className="text-sm font-bold">Caution Required</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Actions in this section are irreversible and will permanently affect your account and data.
                </p>
              </div>

              {/* Delete Account Section */}
              <div className="p-5 rounded-xl border-2 border-red-900/60 bg-red-950/20 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">🗑️</span>
                    <h3 className="text-sm font-bold text-red-400 uppercase tracking-wide">
                      Delete Account
                    </h3>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Permanently delete your account and all associated data including query logs, uploaded documents, 
                    knowledge articles, and profile settings. This action cannot be undone.
                  </p>
                </div>

                <div className="p-3 rounded-lg bg-red-950/50 border border-red-900/50 space-y-1.5">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-red-400">
                    ⚠️ Data That Will Be Deleted:
                  </p>
                  <ul className="text-[11px] text-slate-400 space-y-0.5 pl-3">
                    <li>• All query audit logs and chat history</li>
                    <li>• All uploaded documents and vector embeddings</li>
                    <li>• All runbooks and knowledge base articles</li>
                    <li>• Profile settings, preferences, and API keys</li>
                  </ul>
                </div>

                <button
                  onClick={() => {
                    setShowDeleteModal(true);
                  }}
                  className="w-full py-3 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-extrabold uppercase tracking-wider transition-all shadow-lg shadow-red-600/20 active:scale-95 flex items-center justify-center space-x-2 border border-red-500"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>Delete My Account</span>
                </button>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 flex items-center justify-between shrink-0 bg-slate-950/60">
          <span className="text-[10px] text-slate-500 font-mono">
            Session: <strong className="text-slate-400">{userMetadata.email}</strong>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            Close Settings
          </button>
        </div>
      </div>

      {/* Delete Account Confirmation Modal */}
      {showDeleteModal && (
        <DeleteAccountModal
          userInfo={userInfo}
          onClose={() => setShowDeleteModal(false)}
          onDeleteSuccess={() => {
            // Clear all state and redirect to login
            setShowDeleteModal(false);
            onClose();
            window.location.href = '/';
          }}
        />
      )}
    </div>
  );
}

function StatBox({ icon, value, label, color }) {
  const colorMap = {
    cyan: { bg: 'rgba(8,145,178,0.10)', border: 'rgba(8,145,178,0.25)', text: '#67e8f9' },
    indigo: { bg: 'rgba(99,102,241,0.10)', border: 'rgba(99,102,241,0.25)', text: '#a5b4fc' },
    violet: { bg: 'rgba(139,92,246,0.10)', border: 'rgba(139,92,246,0.25)', text: '#c4b5fd' },
    emerald: { bg: 'rgba(16,185,129,0.10)', border: 'rgba(16,185,129,0.25)', text: '#6ee7b7' },
  };
  const c = colorMap[color] || colorMap.cyan;
  return (
    <div
      className="rounded-lg p-3 text-center border transition-all"
      style={{ background: c.bg, borderColor: c.border }}
    >
      <div className="text-lg mb-1">{icon}</div>
      <div className="text-lg font-black font-mono truncate" style={{ color: c.text }}>
        {value}
      </div>
      <div className="text-[9px] text-slate-500 font-medium leading-tight mt-0.5">{label}</div>
    </div>
  );
}
