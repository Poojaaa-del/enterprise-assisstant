import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export const AuthPage: React.FC = () => {
  const { login, signup } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form states
  const [identifier, setIdentifier] = useState(''); // username or email for login
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await login({ username_or_email: identifier, password });
      } else {
        await signup({
          email,
          username,
          password,
          full_name: fullName || undefined,
        });
        // Auto-login after successful registration
        await login({ username_or_email: username, password });
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <h2>🛡️ GuardCore Portal</h2>
          <p>{isLogin ? 'Sign in to access your dashboard' : 'Create an account to get started'}</p>
        </div>

        {/* Tab Switcher */}
        <div style={styles.tabs}>
          <button
            type="button"
            style={{ ...styles.tab, ...(isLogin ? styles.activeTab : {}) }}
            onClick={() => { setIsLogin(true); setError(null); }}
          >
            Login
          </button>
          <button
            type="button"
            style={{ ...styles.tab, ...(!isLogin ? styles.activeTab : {}) }}
            onClick={() => { setIsLogin(false); setError(null); }}
          >
            Sign Up
          </button>
        </div>

        {error && <div style={styles.errorBox}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          {!isLogin && (
            <>
              <div style={styles.field}>
                <label style={styles.label}>Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                  style={styles.input}
                />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@company.com"
                  style={styles.input}
                />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Username</label>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  style={styles.input}
                />
              </div>
            </>
          )}

          {isLogin && (
            <div style={styles.field}>
              <label style={styles.label}>Username or Email</label>
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="Username or email"
                style={styles.input}
              />
            </div>
          )}

          <div style={styles.field}>
            <label style={styles.label}>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={styles.input}
            />
          </div>

          <button type="submit" disabled={isSubmitting} style={styles.button}>
            {isSubmitting ? 'Processing...' : isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
};

// Inline minimal styles so it works immediately without extra CSS setup
const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    fontFamily: 'sans-serif',
  },
  card: {
    width: '100%',
    maxWidth: '420px',
    padding: '2.5rem',
    borderRadius: '12px',
    backgroundColor: '#1e293b',
    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
    border: '1px solid #334155',
  },
  header: {
    textAlign: 'center',
    marginBottom: '1.5rem',
  },
  tabs: {
    display: 'flex',
    marginBottom: '1.5rem',
    borderBottom: '2px solid #334155',
  },
  tab: {
    flex: 1,
    padding: '0.75rem',
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: 'bold',
  },
  activeTab: {
    color: '#38bdf8',
    borderBottom: '2px solid #38bdf8',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
  },
  label: {
    fontSize: '0.875rem',
    color: '#cbd5e1',
  },
  input: {
    padding: '0.75rem',
    borderRadius: '6px',
    border: '1px solid #475569',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    fontSize: '1rem',
  },
  button: {
    marginTop: '0.5rem',
    padding: '0.75rem',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#0284c7',
    color: '#fff',
    fontSize: '1rem',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  errorBox: {
    padding: '0.75rem',
    borderRadius: '6px',
    backgroundColor: '#7f1d1d',
    color: '#fecaca',
    fontSize: '0.875rem',
    marginBottom: '1rem',
  },
};