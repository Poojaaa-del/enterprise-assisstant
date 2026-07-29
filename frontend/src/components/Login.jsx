// frontend/src/components/Login.jsx
import React, { useState } from "react";

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // FastAPI OAuth2 standard uses form-urlencoded payload
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch("http://localhost:8000/api/v1/auth/token", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed. Check credentials.");
      }

      // Store JWT token securely in browser storage
      localStorage.setItem("token", data.access_token);
      onLoginSuccess(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.badge}>GUARD.CORE // AUTH</div>
          <h2 style={styles.title}>EMKA Enterprise Control Hub</h2>
          <p style={styles.subtitle}>Enter administrative credentials to proceed</p>
        </div>

        {error && <div style={styles.errorBox}>⚠️ {error}</div>}

        <form onSubmit={handleLogin} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Username / Identity</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin"
              required
              style={styles.input}
            />
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Password Key</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              style={styles.input}
            />
          </div>

          <button type="submit" disabled={loading} style={styles.button}>
            {loading ? "Authenticating Matrix..." : "🔑 Authenticate Session"}
          </button>
        </form>

        <div style={styles.footerNote}>
          Default credentials: <code>admin</code> / <code>password123</code>
        </div>
      </div>
    </div>
  );
}

// Inline Styles matching dark cyber-security theme
const styles = {
  overlay: {
    minHeight: "100vh",
    backgroundColor: "#0a0c10",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
    color: "#e2e8f0",
  },
  card: {
    width: "100%",
    maxWidth: "420px",
    backgroundColor: "#111827",
    border: "1px solid #1f2937",
    borderRadius: "12px",
    padding: "32px",
    boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  },
  header: {
    textAlign: "center",
    marginBottom: "24px",
  },
  badge: {
    display: "inline-block",
    fontSize: "11px",
    fontWeight: "700",
    letterSpacing: "1px",
    color: "#38bdf8",
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    padding: "4px 8px",
    borderRadius: "4px",
    marginBottom: "12px",
  },
  title: {
    margin: "0 0 6px 0",
    fontSize: "20px",
    fontWeight: "700",
    color: "#f8fafc",
  },
  subtitle: {
    margin: 0,
    fontSize: "13px",
    color: "#94a3b8",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  inputGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "12px",
    fontWeight: "600",
    color: "#cbd5e1",
  },
  input: {
    backgroundColor: "#030712",
    border: "1px solid #374151",
    borderRadius: "6px",
    padding: "10px 14px",
    fontSize: "14px",
    color: "#f8fafc",
    outline: "none",
  },
  button: {
    backgroundColor: "#2563eb",
    color: "#ffffff",
    fontWeight: "600",
    fontSize: "14px",
    padding: "12px",
    borderRadius: "6px",
    border: "none",
    cursor: "pointer",
    marginTop: "6px",
  },
  errorBox: {
    backgroundColor: "rgba(239, 68, 68, 0.1)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    color: "#fca5a5",
    fontSize: "13px",
    padding: "10px",
    borderRadius: "6px",
    marginBottom: "16px",
  },
  footerNote: {
    marginTop: "24px",
    textAlign: "center",
    fontSize: "12px",
    color: "#64748b",
  }
};