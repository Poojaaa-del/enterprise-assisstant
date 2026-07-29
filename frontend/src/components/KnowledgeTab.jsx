// // KnowledgeTab.jsx
// import React, { useState, useEffect } from 'react';

// // Use environment variable or fallback to localhost
// const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// // Helper to pull Bearer token from localStorage
// const getAuthHeaders = () => {
//   const token = localStorage.getItem('token') || localStorage.getItem('access_token');
//   return token ? { Authorization: `Bearer ${token}` } : {};
// };

// const SAMPLE_ARTICLES = [
//   {
//     title: 'Database Connection Timeout SOP',
//     category: 'RUNBOOK',
//     author: 'DevOps Core',
//     content: "When PostgreSQL connection pool is exhausted (max_connections = 100), check active connections via SELECT * FROM pg_stat_activity WHERE state = 'active'. If connections exceed 90%, restart pgbouncer pooler service or scale reader replicas. Increase connection timeout setting from 30s to 60s in database.yml."
//   },
//   {
//     title: 'Kubernetes OOMKilled Troubleshooting',
//     category: 'INCIDENT',
//     author: 'SRE Ops',
//     content: 'Pods terminating with Exit Code 137 (OOMKilled) indicate memory limit violations. Inspect pod memory metrics using kubectl top pod -n production. Update Deployment resources.limits.memory from 512Mi to 2Gi. Enable HeapDumpOnOutOfMemoryError for JVM processes to capture heap dumps.'
//   },
//   {
//     title: 'OAuth 500 Rate Limit Runbook',
//     category: 'COMPLIANCE',
//     author: 'Security SecOps',
//     content: 'HTTP 500 errors during OAuth token exchange indicate rate limit throttling from Google/Auth0 IDP providers. Implement exponential backoff retry with jitter (max 5 retries, base delay 1000ms). Verify JWT payload claims contain valid sub, email, and exp claims. Audit API key rotation schedule every 90 days.'
//   }
// ];

// export default function KnowledgeTab() {
//   const [files, setFiles] = useState([]);
//   const [uploading, setUploading] = useState(false);
//   const [loadingSamples, setLoadingSamples] = useState(false);
//   const [selectedFile, setSelectedFile] = useState(null);
//   const [statusMsg, setStatusMsg] = useState('');

//   useEffect(() => {
//     fetchActiveInventory();
//   }, []);

//   const fetchActiveInventory = async () => {
//     try {
//       const res = await fetch(`${API_BASE}/api/v1/knowledge/files`, {
//         headers: getAuthHeaders(),
//       });
//       const data = await res.json();
//       if (data.status === 'SUCCESS') setFiles(data.files || []);
//     } catch (err) {
//       console.error("Failed to sync vector list", err);
//     }
//   };

//   const handleLoadSampleArticles = async () => {
//     setLoadingSamples(true);
//     setStatusMsg('');
//     try {
//       for (const article of SAMPLE_ARTICLES) {
//         const res = await fetch(`${API_BASE}/api/v1/knowledge/articles`, {
//           method: 'POST',
//           headers: {
//             'Content-Type': 'application/json',
//             ...getAuthHeaders(),
//           },
//           body: JSON.stringify(article),
//         });

//         if (!res.ok) {
//           throw new Error(`Failed to ingest article: ${article.title}`);
//         }
//       }
//       setStatusMsg('✅ Sample runbooks & knowledge articles ingested successfully!');
//       fetchActiveInventory();
//     } catch (err) {
//       console.error('Failed to load sample articles:', err);
//       setStatusMsg('⚠️ Error loading sample articles into server.');
//     } finally {
//       setLoadingSamples(false);
//     }
//   };

//   const handleUpload = async (e) => {
//     e.preventDefault();
//     if (!selectedFile) return;

//     setUploading(true);
//     setStatusMsg('');
//     const formData = new FormData();
//     // FIXED: Must append 'files' (plural) to match backend List[UploadFile]
//     formData.append('files', selectedFile);

//     try {
//       const res = await fetch(`${API_BASE}/api/v1/knowledge/upload`, {
//         method: 'POST',
//         headers: getAuthHeaders(), // FormData auto-sets Content-Type boundary
//         body: formData,
//       });
//       const data = await res.json();

//       if (res.ok || data.status === 'processing') {
//         setStatusMsg(`✅ ${data.detail || 'File submitted for background vector indexing.'}`);
//         setSelectedFile(null);
//         if (document.getElementById('file-input')) {
//           document.getElementById('file-input').value = '';
//         }
//         setTimeout(fetchActiveInventory, 1500);
//       } else {
//         setStatusMsg(`❌ Error: ${data.detail || 'Upload failed.'}`);
//       }
//     } catch (err) {
//       setStatusMsg('❌ Server connectivity timeout.');
//     } finally {
//       setUploading(false);
//     }
//   };

//   const handleDeleteFile = async (fileId) => {
//     if (!window.confirm('Are you sure you want to delete this document from vector memory?')) return;

//     try {
//       const res = await fetch(`${API_BASE}/api/v1/knowledge/files/${fileId}`, {
//         method: 'DELETE',
//         headers: getAuthHeaders(),
//       });
//       if (res.ok) {
//         setFiles((prev) => prev.filter((f) => f.id !== fileId));
//       } else {
//         alert('Failed to delete file.');
//       }
//     } catch (err) {
//       console.error('Delete file error:', err);
//     }
//   };

//   return (
//     <div className="p-6 max-w-4xl mx-auto space-y-8 animate-fade-in">
//       <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
//         <div>
//           <h2 className="text-xl font-extrabold text-white tracking-wide uppercase">📚 Knowledge Base Repository</h2>
//           <p className="text-xs text-slate-400 mt-1 leading-relaxed">
//             Provide direct plain text files (.txt, .pdf, .docx) containing security regulations or corporate guidelines to append them into the active RAG vector index.
//           </p>
//         </div>
//       </div>

//       {/* Upload Console Interface Card */}
//       <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 shadow-2xl relative overflow-hidden ring-1 ring-slate-800/50">
//         <h3 className="text-xs font-black uppercase tracking-widest text-indigo-300 mb-4">Inject New Document / Policy</h3>

//         <form onSubmit={handleUpload} className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center">
//           <input
//             id="file-input"
//             type="file"
//             accept=".txt,.pdf,.docx,.csv"
//             onChange={(e) => setSelectedFile(e.target.files[0])}
//             className="flex-1 text-xs font-mono text-slate-300 bg-slate-950/90 border border-slate-800 rounded-xl p-3 file:mr-4 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-[10px] file:font-black file:uppercase file:tracking-wider file:bg-indigo-500/10 file:text-indigo-400 hover:file:bg-indigo-500/20 file:cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-500"
//           />
//           <button
//             type="submit"
//             disabled={uploading || !selectedFile}
//             className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-extrabold text-xs rounded-xl shadow-lg transition-all transform active:scale-95 tracking-widest uppercase cursor-pointer"
//           >
//             {uploading ? 'Parsing Vector Embeddings...' : 'Sync to RAG Index'}
//           </button>
//         </form>

//         {statusMsg && (
//           <p className={`text-xs font-mono mt-4 font-bold ${statusMsg.includes('❌') ? 'text-rose-400' : 'text-emerald-400'}`}>
//             {statusMsg}
//           </p>
//         )}
//       </div>

//       {/* Inventory System Files Catalog Table */}
//       <div className="space-y-3">
//         <div className="flex justify-between items-center">
//           <h3 className="text-xs font-black text-slate-400 tracking-widest uppercase">Loaded Reference Contexts</h3>
//           <button
//             onClick={fetchActiveInventory}
//             className="text-[11px] text-slate-400 hover:text-cyan-400 font-mono cursor-pointer"
//           >
//             🔄 Refresh List
//           </button>
//         </div>

//         <div className="bg-slate-950/40 backdrop-blur-xl border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl ring-1 ring-slate-800/50">
//           {files.length === 0 ? (
//             <div className="text-center py-16 text-xs text-slate-500 font-mono tracking-wide space-y-3">
//               <p>SYSTEM CONRELATION WARNING: No secondary index maps discovered.</p>
//               <button
//                 onClick={handleLoadSampleArticles}
//                 disabled={loadingSamples}
//                 className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-bold transition-all shadow-md inline-flex items-center gap-1.5 cursor-pointer"
//               >
//                 {loadingSamples ? '⏳ Ingesting Samples...' : '⚡ Load Sample Knowledge Base Articles'}
//               </button>
//             </div>
//           ) : (
//             <div className="overflow-x-auto">
//               <table className="w-full text-xs">
//                 <thead>
//                   <tr className="border-b border-slate-800/50 bg-slate-900/20">
//                     <th className="px-4 py-3 text-left font-black text-slate-300 tracking-wider">File</th>
//                     <th className="px-4 py-3 text-center font-black text-slate-300 tracking-wider">Chunks</th>
//                     <th className="px-4 py-3 text-center font-black text-slate-300 tracking-wider">Status</th>
//                     <th className="px-4 py-3 text-center font-black text-slate-300 tracking-wider">Actions</th>
//                   </tr>
//                 </thead>
//                 <tbody className="divide-y divide-slate-800/50">
//                   {files.map((file) => (
//                     <tr
//                       key={file.id}
//                       className="hover:bg-slate-900/20 transition-all duration-200 bg-slate-900/10"
//                     >
//                       <td className="px-4 py-3 flex items-center space-x-2">
//                         <span className="text-sm">📄</span>
//                         <span className="font-mono text-slate-200 truncate max-w-xs sm:max-w-md">
//                           {file.file_name || file.filename}
//                         </span>
//                       </td>
//                       <td className="px-4 py-3 text-center font-mono text-slate-300">
//                         {file.chunks || file.chunk_count || '1'}
//                       </td>
//                       <td className="px-4 py-3 text-center">
//                         <span className="text-[9px] font-black tracking-widest uppercase px-2.5 py-1 rounded-lg border bg-emerald-950/30 border-emerald-900/50 text-emerald-400 shadow-sm whitespace-nowrap">
//                           {file.status || 'Indexed'}
//                         </span>
//                       </td>
//                       <td className="px-4 py-3 text-center">
//                         <button
//                           onClick={() => handleDeleteFile(file.id)}
//                           className="text-slate-500 hover:text-red-400 p-1 transition-colors text-xs cursor-pointer"
//                           title="Purge File & Vectors"
//                         >
//                           🗑️
//                         </button>
//                       </td>
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             </div>
//           )}
//         </div>
//       </div>
//     </div>
//   );
// }

// KnowledgeTab.jsx
import React, { useState, useEffect } from 'react';

// Use environment variable or fallback to localhost
const API_BASE = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Helper to pull Bearer token from localStorage
const getAuthHeaders = () => {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const SAMPLE_ARTICLES = [
  {
    title: 'Database Connection Timeout SOP',
    category: 'RUNBOOK',
    author: 'DevOps Core',
    content: "When PostgreSQL connection pool is exhausted (max_connections = 100), check active connections via SELECT * FROM pg_stat_activity WHERE state = 'active'. If connections exceed 90%, restart pgbouncer pooler service or scale reader replicas. Increase connection timeout setting from 30s to 60s in database.yml."
  },
  {
    title: 'Kubernetes OOMKilled Troubleshooting',
    category: 'INCIDENT',
    author: 'SRE Ops',
    content: 'Pods terminating with Exit Code 137 (OOMKilled) indicate memory limit violations. Inspect pod memory metrics using kubectl top pod -n production. Update Deployment resources.limits.memory from 512Mi to 2Gi. Enable HeapDumpOnOutOfMemoryError for JVM processes to capture heap dumps.'
  },
  {
    title: 'OAuth 500 Rate Limit Runbook',
    category: 'COMPLIANCE',
    author: 'Security SecOps',
    content: 'HTTP 500 errors during OAuth token exchange indicate rate limit throttling from Google/Auth0 IDP providers. Implement exponential backoff retry with jitter (max 5 retries, base delay 1000ms). Verify JWT payload claims contain valid sub, email, and exp claims. Audit API key rotation schedule every 90 days.'
  }
];

export default function KnowledgeTab() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    fetchActiveInventory();
  }, []);

  // FIXED: Fetch BOTH files and articles so articles actually appear in the table
  const fetchActiveInventory = async () => {
    try {
      const [filesRes, articlesRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/knowledge/files`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/v1/knowledge/articles`, { headers: getAuthHeaders() }).catch(() => null),
      ]);

      let combinedInventory = [];

      if (filesRes.ok) {
        const filesData = await filesRes.json();
        const rawFiles = Array.isArray(filesData) ? filesData : (filesData.files || filesData.data || []);
        const fileList = rawFiles.map((f) => ({
          ...f,
          is_article: false,
        }));
        combinedInventory.push(...fileList);
      }

      if (articlesRes && articlesRes.ok) {
        const articlesData = await articlesRes.json();
        const articleList = (
          articlesData.articles || 
          articlesData.data || 
          (Array.isArray(articlesData) ? articlesData : [])
        ).map((a) => ({
          ...a,
          is_article: true,
        }));
        combinedInventory.push(...articleList);
      }

      setFiles(combinedInventory);
    } catch (err) {
      console.error('Failed to sync inventory list', err);
    }
  };

  const handleLoadSampleArticles = async () => {
    setLoadingSamples(true);
    setStatusMsg('');
    try {
      for (const article of SAMPLE_ARTICLES) {
        const res = await fetch(`${API_BASE}/api/v1/knowledge/articles`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify(article),
        });

        if (!res.ok) {
          throw new Error(`Failed to ingest article: ${article.title}`);
        }
      }
      setStatusMsg('✅ Sample runbooks & knowledge articles ingested successfully!');
      fetchActiveInventory();
    } catch (err) {
      console.error('Failed to load sample articles:', err);
      setStatusMsg('⚠️ Error loading sample articles into server.');
    } finally {
      setLoadingSamples(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setStatusMsg('');
    const formData = new FormData();
    formData.append('files', selectedFile);

    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      });
      const data = await res.json();

      if (res.ok || data.status === 'processing') {
        setStatusMsg(`✅ ${data.detail || 'File submitted for background vector indexing.'}`);
        setSelectedFile(null);
        if (document.getElementById('file-input')) {
          document.getElementById('file-input').value = '';
        }
        setTimeout(fetchActiveInventory, 1500);
      } else {
        setStatusMsg(`❌ Error: ${data.detail || 'Upload failed.'}`);
      }
    } catch (err) {
      setStatusMsg('❌ Server connectivity timeout.');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteFile = async (fileId) => {
    if (!fileId) return;
    if (!window.confirm('Are you sure you want to delete this document from vector memory?')) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/files/${fileId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setFiles((prev) => prev.filter((f) => (f.id || f._id || f.title) !== fileId));
      } else {
        alert('Failed to delete file.');
      }
    } catch (err) {
      console.error('Delete file error:', err);
    }
  };

  const handleDeleteArticle = async (articleId) => {
    if (!articleId) return;
    if (!window.confirm('Are you sure you want to delete this runbook from vector memory?')) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/articles/${articleId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setFiles((prev) => prev.filter((f) => (f.id || f._id || f.title) !== articleId));
      } else {
        alert('Failed to delete runbook.');
      }
    } catch (err) {
      console.error('Delete article error:', err);
    }
  };

  const handleDeleteItem = (item) => {
    const resolvedId = item.id || item._id || item.title;
    if (item.is_article || item.category || item.type === 'article') {
      handleDeleteArticle(resolvedId);
    } else {
      handleDeleteFile(resolvedId);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-wide uppercase">📚 Knowledge Base Repository</h2>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            Provide direct plain text files (.txt, .pdf, .docx) containing security regulations or corporate guidelines to append them into the active RAG vector index.
          </p>
        </div>
      </div>

      {/* Upload Console Interface Card */}
      <div className="bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-6 shadow-2xl relative overflow-hidden ring-1 ring-slate-800/50">
        <h3 className="text-xs font-black uppercase tracking-widest text-indigo-300 mb-4">Inject New Document / Policy</h3>

        <form onSubmit={handleUpload} className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center">
          <input
            id="file-input"
            type="file"
            accept=".txt,.pdf,.docx,.csv"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            className="flex-1 text-xs font-mono text-slate-300 bg-slate-950/90 border border-slate-800 rounded-xl p-3 file:mr-4 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-[10px] file:font-black file:uppercase file:tracking-wider file:bg-indigo-500/10 file:text-indigo-400 hover:file:bg-indigo-500/20 file:cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={uploading || !selectedFile}
            className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-extrabold text-xs rounded-xl shadow-lg transition-all transform active:scale-95 tracking-widest uppercase cursor-pointer"
          >
            {uploading ? 'Parsing Vector Embeddings...' : 'Sync to RAG Index'}
          </button>
        </form>

        {statusMsg && (
          <p className={`text-xs font-mono mt-4 font-bold ${statusMsg.includes('❌') ? 'text-rose-400' : 'text-emerald-400'}`}>
            {statusMsg}
          </p>
        )}
      </div>

      {/* Inventory System Files Catalog Table */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-xs font-black text-slate-400 tracking-widest uppercase">Loaded Reference Contexts</h3>
          <button
            onClick={fetchActiveInventory}
            className="text-[11px] text-slate-400 hover:text-cyan-400 font-mono cursor-pointer"
          >
            🔄 Refresh List
          </button>
        </div>

        <div className="bg-slate-950/40 backdrop-blur-xl border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl ring-1 ring-slate-800/50">
          {files.length === 0 ? (
            <div className="text-center py-16 text-xs text-slate-500 font-mono tracking-wide space-y-3">
              <p>SYSTEM CORRELATION WARNING: No secondary index maps discovered.</p>
              <button
                onClick={handleLoadSampleArticles}
                disabled={loadingSamples}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-bold transition-all shadow-md inline-flex items-center gap-1.5 cursor-pointer"
              >
                {loadingSamples ? '⏳ Ingesting Samples...' : '⚡ Load Sample Knowledge Base Articles'}
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800/50 bg-slate-900/20">
                    <th className="px-4 py-3 text-left font-black text-slate-300 tracking-wider">File / Runbook</th>
                    <th className="px-4 py-3 text-center font-black text-slate-300 tracking-wider">Chunks</th>
                    <th className="px-4 py-3 text-center font-black text-slate-300 tracking-wider">Status</th>
                    <th className="px-4 py-3 text-center font-black text-slate-300 tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {files.map((file) => {
                    const isArticle = file.is_article || file.category || file.type === 'article';
                    return (
                      <tr
                        key={file.id || file.title}
                        className="hover:bg-slate-900/20 transition-all duration-200 bg-slate-900/10"
                      >
                        <td className="px-4 py-3 flex items-center space-x-2">
                          <span className="text-sm">{isArticle ? '📖' : '📄'}</span>
                          <span className="font-mono text-slate-200 truncate max-w-xs sm:max-w-md">
                            {file.file_name || file.filename || file.title}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center font-mono text-slate-300">
                          {file.chunks || file.chunk_count || '1'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-[9px] font-black tracking-widest uppercase px-2.5 py-1 rounded-lg border bg-emerald-950/30 border-emerald-900/50 text-emerald-400 shadow-sm whitespace-nowrap">
                            {file.status || 'Indexed'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {/* HIGH-VISIBILITY RED DELETE BUTTON */}
                          <button
                            onClick={() => handleDeleteItem(file)}
                            className="px-2.5 py-1 bg-red-500/10 hover:bg-red-500/25 text-red-400 border border-red-500/30 hover:border-red-500/60 rounded-lg text-xs font-bold transition-all cursor-pointer inline-flex items-center gap-1 shadow-sm"
                            title={isArticle ? 'Purge Runbook & Vector Embeddings' : 'Purge File & Vectors'}
                          >
                            <span>🗑️</span>
                            <span>Delete</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}