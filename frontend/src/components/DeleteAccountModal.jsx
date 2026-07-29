// frontend/src/components/DeleteAccountModal.jsx
import React, { useState, useEffect } from 'react';
import { deleteUserAccount } from '../services/api';

export default function DeleteAccountModal({ userInfo, onClose, onDeleteSuccess }) {
  const [confirmText, setConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const isDeleteEnabled = confirmText.trim() === 'DELETE';

  const handleDelete = async () => {
    if (!isDeleteEnabled) return;

    setErrorMessage('');
    setDeleting(true);

    try {
      await deleteUserAccount();

      // Clear all local storage data
      localStorage.clear();

      // Notify parent and redirect
      if (onDeleteSuccess) {
        onDeleteSuccess();
      }
    } catch (error) {
      setErrorMessage(error.message || 'Failed to delete account. Please try again.');
      setDeleting(false);
    }
  };

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && !deleting) onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose, deleting]);

  // Backdrop click handler
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget && !deleting) {
      onClose();
    }
  };

  const userEmail = userInfo?.email || 'your account';

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.90)', backdropFilter: 'blur(12px)' }}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="Delete Account Confirmation"
    >
      {/* Modal Container */}
      <div
        className="relative w-full max-w-lg rounded-2xl border shadow-2xl overflow-hidden"
        style={{
          background: 'linear-gradient(145deg, rgba(15,23,42,0.98) 0%, rgba(15,23,42,0.96) 100%)',
          borderColor: 'rgba(239,68,68,0.4)',
          boxShadow: '0 0 0 1px rgba(239,68,68,0.25), 0 32px 64px -12px rgba(0,0,0,0.9)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Danger Bar */}
        <div
          className="h-1.5 w-full"
          style={{ background: 'linear-gradient(90deg, #dc2626 0%, #ef4444 50%, #f87171 100%)' }}
        />

        {/* Modal Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-red-900/30">
          <div className="flex items-start space-x-3">
            <div className="w-10 h-10 rounded-full bg-red-950/60 border border-red-800/60 flex items-center justify-center shrink-0">
              <span className="text-xl">⚠️</span>
            </div>
            <div>
              <h2 className="text-base font-black uppercase tracking-wide text-red-400">
                Delete Account
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                This action is permanent and cannot be undone
              </p>
            </div>
          </div>
          {!deleting && (
            <button
              onClick={onClose}
              className="text-slate-500 hover:text-slate-200 transition-colors p-1.5 rounded-lg hover:bg-slate-800"
              aria-label="Close modal"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Modal Content */}
        <div className="px-6 py-5 space-y-5">
          {/* Warning Message */}
          <div className="p-4 rounded-lg bg-red-950/40 border border-red-900/50 space-y-3">
            <div className="flex items-center space-x-2 text-red-400">
              <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span className="text-sm font-bold">Permanent Account Deletion</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              You are about to permanently delete your account: <strong className="font-mono text-red-300">{userEmail}</strong>
            </p>
          </div>

          {/* What Will Be Deleted */}
          <div className="space-y-2.5">
            <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
              The following data will be permanently deleted:
            </p>
            <ul className="space-y-2">
              <DeletedItem icon="📋" text="All query audit logs and chat history" />
              <DeletedItem icon="📂" text="All uploaded documents and knowledge base files" />
              <DeletedItem icon="📄" text="All runbooks and knowledge articles" />
              <DeletedItem icon="👤" text="Your profile, settings, and preferences" />
              <DeletedItem icon="🔑" text="API keys and authentication credentials" />
            </ul>
          </div>

          {/* Confirmation Input */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300">
              Type <span className="font-mono text-red-400 bg-red-950/50 px-1.5 py-0.5 rounded">DELETE</span> to confirm:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="Type DELETE here..."
              disabled={deleting}
              className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20 font-mono disabled:opacity-50 disabled:cursor-not-allowed"
              autoComplete="off"
              autoFocus
            />
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-mono flex items-start space-x-2">
              <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>{errorMessage}</span>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 border-t border-red-900/30 flex items-center justify-end space-x-3 bg-slate-950/60">
          <button
            onClick={onClose}
            disabled={deleting}
            className="px-4 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-slate-300 rounded-lg border border-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={!isDeleteEnabled || deleting}
            className="px-5 py-2 text-xs font-extrabold uppercase tracking-wider bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-all shadow-lg shadow-red-600/20 active:scale-95 flex items-center space-x-2"
          >
            {deleting ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Deleting Account...</span>
              </>
            ) : (
              <span>Permanently Delete Account</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function DeletedItem({ icon, text }) {
  return (
    <li className="flex items-start space-x-2.5 text-xs text-slate-400">
      <span className="shrink-0 text-base">{icon}</span>
      <span className="leading-relaxed">{text}</span>
    </li>
  );
}
