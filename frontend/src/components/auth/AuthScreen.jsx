// src/components/auth/AuthScreen.jsx

import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { loginApi, signupApi, googleAuthApi } from '../../services/api';
import { setStoredToken } from '../../utils/auth';

export default function AuthScreen({ onLoginSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Helper to clear all state when switching tabs between Sign In and Create Account
  const handleTabSwitch = (targetIsSignUp) => {
    setIsSignUp(targetIsSignUp);
    setEmail('');
    setPassword('');
    setError('');
    setSuccessMsg('');
    setShowPassword(false);
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    if (!credentialResponse?.credential) {
      setError('Google login failed: Credential missing.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const data = await googleAuthApi(credentialResponse.credential);
      if (data?.access_token) {
        setStoredToken(data.access_token);
        onLoginSuccess(data.access_token);
      } else {
        throw new Error('Invalid server response: Access token missing.');
      }
    } catch (err) {
      setError(err.message || 'Google authentication failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleError = () => {
    setError('Google Sign-In failed or was cancelled.');
  };

  // const handleSubmit = async (e) => {
  //   e.preventDefault();
  //   setError('');
  //   setSuccessMsg('');

  //   // Client-side validation: Email format regex check
  //   const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  //   const trimmedEmail = email.trim();
  //   if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
  //     setError('Please enter a valid email address.');
  //     return;
  //   }

  //   // Client-side validation: Password minimum length check (8 characters)
  //   if (!password || password.length < 8) {
  //     setError('Password must be at least 8 characters long.');
  //     return;
  //   }

  //   setSubmitting(true);

  //   try {
  //     if (isSignUp) {
  //       await signupApi(trimmedEmail, trimmedEmail, password);
  //       setSuccessMsg('Account created! Logging you in automatically...');

  //       // Auto-login attempt after sign up
  //       try {
  //         const loginData = await loginApi(trimmedEmail, trimmedEmail, password);
  //         if (loginData?.access_token) {
  //           setStoredToken(loginData.access_token);
  //           onLoginSuccess(loginData.access_token);
  //           return;
  //         } else {
  //           handleTabSwitch(false);
  //           setError('Account created successfully! Auto-login failed—please enter your credentials to log in.');
  //         }
  //       } catch {
  //         handleTabSwitch(false);
  //         setError('Account created successfully! Auto-login failed—please enter your credentials to log in.');
  //       }
  //     } else {
  //       const loginData = await loginApi(trimmedEmail, trimmedEmail, password);
  //       if (loginData?.access_token) {
  //         setStoredToken(loginData.access_token);
  //         onLoginSuccess(loginData.access_token);
  //       } else {
  //         throw new Error('Invalid server response: Access token missing.');
  //       }
  //     }
  //   } catch (err) {
  //     if (err.name === 'TypeError' || err.message?.includes('fetch')) {
  //       setError('Unable to connect to server. Please check your network connection.');
  //     } else {
  //       setError(err.message || 'An unexpected error occurred.');
  //     }
  //   } finally {
  //     setSubmitting(false);
  //   }
  // };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    // Client-side validation: Email format regex check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      setError('Please enter a valid email address.');
      return;
    }

    // Client-side validation: Password minimum length check (8 characters)
    if (!password || password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setSubmitting(true);

    try {
      if (isSignUp) {
        await signupApi(trimmedEmail, trimmedEmail, password);
        
        // Switch to Sign In tab and show verification prompt
        handleTabSwitch(false);
        setSuccessMsg('Check your email inbox to verify your account before logging in.');
      } else {
        const loginData = await loginApi(trimmedEmail, trimmedEmail, password);
        if (loginData?.access_token) {
          setStoredToken(loginData.access_token);
          onLoginSuccess(loginData.access_token);
        } else {
          throw new Error('Invalid server response: Access token missing.');
        }
      }
    } catch (err) {
      if (err.name === 'TypeError' || err.message?.includes('fetch')) {
        setError('Unable to connect to server. Please check your network connection.');
      } else {
        setError(err.message || 'An unexpected error occurred.');
      }
    } finally {
      setSubmitting(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-extrabold text-white tracking-tight mb-2">
            LogTriage AI
          </h1>
          <p className="text-slate-400 text-sm">
            {isSignUp ? 'Create a new account' : 'Sign in to access console'}
          </p>
        </div>

        {/* Tab Switch Header */}
        <div className="flex border-b border-slate-800 mb-6">
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleTabSwitch(false)}
            className={`flex-1 py-2.5 text-xs font-semibold border-b-2 transition-colors disabled:opacity-50 ${
              !isSignUp
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleTabSwitch(true)}
            className={`flex-1 py-2.5 text-xs font-semibold border-b-2 transition-colors disabled:opacity-50 ${
              isSignUp
                ? 'border-cyan-500 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Create Account
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/80 border border-red-800 rounded-lg text-red-300 text-xs flex items-start space-x-2">
            <span className="shrink-0 mt-0.5">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 bg-emerald-950/80 border border-emerald-800 rounded-lg text-emerald-300 text-xs flex items-start space-x-2">
            <span className="shrink-0 mt-0.5">✅</span>
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              disabled={submitting}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="admin@company.com"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                disabled={submitting}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 pr-10 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder="••••••••"
              />
              <button
                type="button"
                disabled={submitting}
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed p-1 transition-colors"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2 flex items-center justify-center space-x-2"
          >
            {submitting ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Processing...</span>
              </>
            ) : isSignUp ? (
              'Create Account'
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="mt-6 text-center border-t border-slate-800 pt-4 space-y-4">
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleTabSwitch(!isSignUp)}
            className="text-xs text-cyan-400 hover:underline disabled:opacity-50 disabled:cursor-not-allowed block mx-auto"
          >
            {isSignUp
              ? 'Already have an account? Sign In'
              : "Don't have an account? Sign Up"}
          </button>

          <div className="pt-2 border-t border-slate-800/80 flex flex-col items-center space-y-2">
            <span className="text-[11px] text-slate-400 font-medium">Or continue with Google</span>
            <div className="flex justify-center w-full">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                theme="filled_dark"
                shape="pill"
                text="continue_with"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
