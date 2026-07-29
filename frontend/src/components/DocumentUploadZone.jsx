import React, { useState } from 'react';
import { API_BASE } from '../utils/constants';
import { getAuthHeaders } from '../utils/auth';

export default function DocumentUploadZone({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [classification, setClassification] = useState('GENERAL');
  const [permittedRole, setPermittedRole] = useState('USER');
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ type: '', text: '' });

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatusMessage({ type: '', text: '' });
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setStatusMessage({ type: 'error', text: 'Please select a file first!' });
      return;
    }

    setLoading(true);
    setStatusMessage({ type: 'info', text: 'Parser Agent extracting layout data...' });

    // Prepare multi-part form payload required by FastAPI (/upload expects 'files')
    const formData = new FormData();
    formData.append('files', file);
    formData.append('classification', classification);
    formData.append('permitted_role', permittedRole);

    try {
      // IMPORTANT: Do NOT pass Content-Type here. The browser must auto-set
      // "multipart/form-data; boundary=..." based on the FormData body.
      // Passing Content-Type: application/json (from getAuthHeaders) destroys
      // the boundary and causes FastAPI to return HTTP 422 Unprocessable Entity.
      const token = localStorage.getItem('token');
      const uploadHeaders = token ? { Authorization: `Bearer ${token}` } : {};

      const response = await fetch(`${API_BASE}/api/v1/knowledge/upload`, {
        method: 'POST',
        headers: uploadHeaders,
        body: formData,
      });

      const data = await response.json();

      if (response.ok && (data.status === 'SUCCESS' || response.status === 202 || data.status === 'processing')) {
        setStatusMessage({ type: 'success', text: `✅ ${data.filename || file.name} queued for indexing!` });
        setFile(null); // Reset file input
        if (onUploadSuccess) onUploadSuccess();
      } else {
        setStatusMessage({ type: 'error', text: `❌ Upload Failed: ${data.detail || 'Unknown parser error'}` });
      }
    } catch (err) {
      setStatusMessage({ type: 'error', text: `❌ Connection Refused: Ensure backend is running.` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.card}>
      <h3 style={styles.title}>📂 Document Parser Ingestion Terminal</h3>
      <p style={styles.subtitle}>Upload enterprise files directly into the ChromaDB Knowledge Matrix</p>
      
      <form onSubmit={handleUpload} style={styles.form}>
        <div style={styles.fileBox}>
          <input 
            type="file" 
            accept=".txt,.csv,.pdf" 
            onChange={handleFileChange} 
            style={styles.fileInput}
            id="enterprise-file-picker"
          />
          <label htmlFor="enterprise-file-picker" style={styles.fileLabel}>
            {file ? `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)` : '📁 Click to choose PDF, CSV, or TXT file'}
          </label>
        </div>

        <div style={styles.metaRow}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>Classification Type</label>
            <select value={classification} onChange={(e) => setClassification(e.target.value)} style={styles.select}>
              <option value="GENERAL">General Guidelines</option>
              <option value="HR">HR Policies</option>
              <option value="TECHNICAL">Technical Documentation</option>
              <option value="FINANCIAL">Financial Tables</option>
            </select>
          </div>

          <div style={styles.inputGroup}>
            <label style={styles.label}>Access Restriction (RBAC)</label>
            <select value={permittedRole} onChange={(e) => setPermittedRole(e.target.value)} style={styles.select}>
              <option value="USER">Standard Employee (User)</option>
              <option value="DEVELOPER">Engineering / Devs</option>
              <option value="HR">HR Department Only</option>
              <option value="ADMIN">Administrative Systems</option>
            </select>
          </div>
        </div>

        <button type="submit" disabled={loading} style={loading ? styles.btnDisabled : styles.btn}>
          {loading ? 'Processing Embeddings...' : '🚀 Stream to Vector Matrix'}
        </button>
      </form>

      {statusMessage.text && (
        <div style={{ ...styles.alert, ...styles[statusMessage.type] }}>
          {statusMessage.text}
        </div>
      )}
    </div>
  );
}

// Inline structural CSS matrix for simple, independent dashboard styling
const styles = {
  card: { background: '#1e1e2e', padding: '24px', borderRadius: '12px', border: '1px solid #313244', color: '#cdd6f4', fontFamily: 'sans-serif', maxWidth: '600px', margin: '20px auto' },
  title: { margin: '0 0 4px 0', fontSize: '18px', color: '#f5c2e7' },
  subtitle: { margin: '0 0 20px 0', fontSize: '13px', color: '#a6adc8' },
  form: { display: 'flex', flexDirection: 'column', gap: '16px' },
  fileBox: { border: '2px dashed #45475a', borderRadius: '8px', padding: '20px', textAlign: 'center', cursor: 'pointer', background: '#11111b' },
  fileInput: { display: 'none' },
  fileLabel: { display: 'block', width: '100%', height: '100%', cursor: 'pointer', fontSize: '14px', color: '#89b4fa' },
  metaRow: { display: 'flex', gap: '16px' },
  inputGroup: { flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' },
  label: { fontSize: '12px', color: '#a6adc8', fontWeight: 'bold' },
  select: { background: '#313244', color: '#cdd6f4', border: '1px solid #45475a', padding: '8px', borderRadius: '6px', cursor: 'pointer' },
  btn: { background: '#a6e3a1', color: '#11111b', border: 'none', padding: '12px', borderRadius: '6px', fontSize: '14px', fontWeight: 'bold', cursor: 'pointer', transition: 'opacity 0.2s' },
  btnDisabled: { background: '#585b70', color: '#a6adc8', border: 'none', padding: '12px', borderRadius: '6px', fontSize: '14px', fontWeight: 'bold', cursor: 'not-allowed' },
  alert: { marginTop: '16px', padding: '12px', borderRadius: '6px', fontSize: '13px' },
  info: { background: 'rgba(137, 180, 250, 0.15)', color: '#89b4fa', border: '1px solid #89b4fa' },
  success: { background: 'rgba(166, 227, 161, 0.15)', color: '#a6e3a1', border: '1px solid #a6e3a1' },
  error: { background: 'rgba(243, 139, 168, 0.15)', color: '#f38ba8', border: '1px solid #f38ba8' }
};