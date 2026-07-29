import { useEffect, useState } from 'react';
import { verifyEmailApi } from '../../services/api';

export default function VerifyEmailPage() {
  const [status, setStatus] = useState('verifying');
  const [message, setMessage] = useState('Verifying your email address...');

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token');
    if (!token) {
      setStatus('error');
      setMessage('Verification token is missing.');
      return;
    }

    let isMounted = true;

    const verifyEmail = async () => {
      try {
        const data = await verifyEmailApi(token);
        if (!isMounted) return;
        setStatus('success');
        setMessage(data?.message || 'Email verified successfully! You can now log in.');
      } catch (err) {
        if (!isMounted) return;
        setStatus('error');
        setMessage(err.message || 'Email verification failed.');
      }
    };

    verifyEmail();

    return () => {
      isMounted = false;
    };
  }, []);

  const isSuccess = status === 'success';
  const isVerifying = status === 'verifying';

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center">
        <div
          className={`mx-auto mb-5 h-12 w-12 rounded-full flex items-center justify-center border ${
            isVerifying
              ? 'border-cyan-700 bg-cyan-950/70 text-cyan-300'
              : isSuccess
              ? 'border-emerald-700 bg-emerald-950/70 text-emerald-300'
              : 'border-red-800 bg-red-950/70 text-red-300'
          }`}
        >
          {isVerifying ? (
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : isSuccess ? (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v4m0 4h.01M5.07 19h13.86A2 2 0 0020.66 16L13.73 4a2 2 0 00-3.46 0L3.34 16a2 2 0 001.73 3z" />
            </svg>
          )}
        </div>

        <h1 className="text-2xl font-extrabold text-white tracking-tight mb-2">
          Email Verification
        </h1>
        <p className="text-sm text-slate-300 mb-6">{message}</p>

        {!isVerifying && (
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-lg bg-cyan-600 hover:bg-cyan-500 px-4 py-2 text-sm font-medium text-white transition-colors"
          >
            Return to Sign In
          </a>
        )}
      </div>
    </div>
  );
}
