# backend/api/knowledge.py
"""
Knowledge Management API
- /upload       : Authenticated multi-file upload with user-scoped ChromaDB indexing
- /files        : List files from knowledge_files table (per-user)
- /files/{id}   : Delete a file record + purge its ChromaDB chunks
- /articles     : CRUD for runbook/article knowledge articles
- /query        : Legacy single-pass RAG query (unauthenticated, kept for backward compat)
- /agent-query  : Full multi-agent pipeline (Planner→Retrieval→Verification→Report)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import os
import sqlite3
import uuid
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from io import BytesIO
import hashlib
from pathlib import Path

from api.auth import get_current_user
from agents import (
    DocumentParserAgent,
    RetrievalAgent,
    PlannerAgent,
    VerificationAgent,
    ReportAgent,
)

# ── Ingestion parsers (kept for legacy process_and_vectorize_file) ─────────────
from ingestion.pdf import parse_pdf
from ingestion.word import parse_docx
from ingestion.excel import parse_spreadsheet
from ingestion.text import parse_txt

# ── Pydantic models ────────────────────────────────────────────────────────────
class RAGQueryRequest(BaseModel):
    question: str

class RAGQueryResponse(BaseModel):
    status: str
    message: str
    citation: str

class ChatMessage(BaseModel):
    role: str
    content: str

class AgentQueryRequest(BaseModel):
    question: str
    chat_history: Optional[List[ChatMessage]] = []

class ArticleCreateRequest(BaseModel):
    title: str
    category: str = "RUNBOOK"
    author: str = ""
    content: str = ""

class FeedbackRequest(BaseModel):
    log_id: Any
    rating: int


# ── Router & paths ─────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Management"])

BASE_DIR      = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = str(BASE_DIR / "knowledge_base_data")
CHROMA_DIR    = str(BASE_DIR / "chroma_db")
DATABASE_PATH = str(BASE_DIR / "triage.db")

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# ── Auto-initialize SQLite tables ──────────────────────────────────────────────
def _init_db_tables():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT DEFAULT 'RUNBOOK',
                author TEXT DEFAULT '',
                content TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER,
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Indexed',
                file_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                status TEXT DEFAULT 'processing',
                chunk_count INTEGER DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                detail TEXT DEFAULT ''
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Table init error: {e}")

_init_db_tables()

# ── ChromaDB client (shared, explicit embedding function) ──────────────────────
try:
    embedding_engine = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection    = chroma_client.get_or_create_collection(
        name="guard_core_nodes",
        embedding_function=embedding_engine,
    )
except Exception as _chroma_init_err:
    print(f"[WARNING] ChromaDB init failed: {_chroma_init_err}. Vector features disabled.")
    chroma_client = None
    collection    = None

groq_client = Groq()

# ── Agent singletons (module-level, lazy-safe) ─────────────────────────────────
_parser_agent   = None
_retrieval_agent = None
_planner_agent  = None
_verifier_agent = None
_report_agent   = None

def _get_agents():
    global _parser_agent, _retrieval_agent, _planner_agent, _verifier_agent, _report_agent
    if _parser_agent is None:
        _parser_agent    = DocumentParserAgent()
        _retrieval_agent = RetrievalAgent()
        _planner_agent   = PlannerAgent()
        _verifier_agent  = VerificationAgent()
        _report_agent    = ReportAgent()
    return _parser_agent, _retrieval_agent, _planner_agent, _verifier_agent, _report_agent


def _role_value(user) -> str:
    role = getattr(user, "role", "USER")
    return str(role.value) if hasattr(role, "value") else str(role or "USER")


# ── Legacy helper (kept for bootstrap auto-sync & unauthenticated /upload) ─────
def process_and_vectorize_file(filename: str, file_path: str, user_id: int, permitted_role: str = "USER"):
    """
    Routes files to ingestion engine, extracts chunks, and saves to ChromaDB.
    Used only when an explicit bootstrap user is configured.
    """
    try:
        if filename.endswith(".pdf"):
            parsed_chunks = parse_pdf(file_path)
        elif filename.endswith((".docx", ".doc")):
            parsed_chunks = parse_docx(file_path)
        elif filename.endswith((".csv", ".xlsx", ".xls")):
            parsed_chunks = parse_spreadsheet(file_path, filename)
        elif filename.endswith(".txt"):
            parsed_chunks = parse_txt(file_path)
        else:
            print(f"[WARNING] [Ingestion] Skipped unsupported type: {filename}")
            return

        if not parsed_chunks:
            print(f"[WARNING] [Ingestion] No text extracted from: {filename}")
            return

        if collection is None:
            print(f"[WARNING] [Ingestion] ChromaDB not available; skipping vectorize for: {filename}")
            return

        documents = [chunk["text"] for chunk in parsed_chunks]
        metadatas = []
        for chunk in parsed_chunks:
            meta = chunk["metadata"]
            meta["source"] = filename
            meta["filename"] = filename
            meta["user_id"] = user_id
            meta["permitted_role"] = permitted_role
            metadatas.append(meta)
        ids = [f"user_{user_id}_{filename}_chunk_{i}" for i in range(len(parsed_chunks))]
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"[INFO] [EMKA Storage Matrix] Vectorized {len(parsed_chunks)} segments for: {filename} (user {user_id})")
    except Exception as e:
        print(f"[ERROR] [Ingestion Collapse]: {str(e)}")


# ── Bootstrap auto-sync on startup ─────────────────────────────────────────────
try:
    bootstrap_user_id = os.getenv("BOOTSTRAP_KNOWLEDGE_USER_ID")
    if collection is not None and os.path.exists(KNOWLEDGE_DIR) and bootstrap_user_id:
        bootstrap_user_id = int(bootstrap_user_id)
        for current_file in os.listdir(KNOWLEDGE_DIR):
            target_path = os.path.join(KNOWLEDGE_DIR, current_file)
            if os.path.isfile(target_path) and current_file.lower().endswith(
                (".txt", ".csv", ".pdf", ".docx", ".xlsx")
            ):
                try:
                    existing = collection.get(ids=[f"user_{bootstrap_user_id}_{current_file}_chunk_0"])
                    if not existing or not existing.get("ids"):
                        print(f"[INFO] [Vector Boot Sync] Indexing: {current_file}")
                        process_and_vectorize_file(current_file, target_path, user_id=bootstrap_user_id)
                except Exception as sync_exc:
                    print(f"[WARNING] [Vector Boot Sync] {current_file}: {sync_exc}")
    elif collection is not None and os.path.exists(KNOWLEDGE_DIR):
        print("[INFO] [Vector Boot Sync] Skipped: BOOTSTRAP_KNOWLEDGE_USER_ID is not set.")
except Exception as _boot_err:
    print(f"[WARNING] [Vector Boot Sync] Boot sync skipped: {_boot_err}")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Async Ingestion Worker & Audit Helpers ────────────────────────────────────
def _update_job_status(job_id: str, status: str, chunk_count: int = 0, file_size: int = 0, detail: str = ""):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE ingestion_jobs
            SET status = ?, chunk_count = ?, file_size = ?, detail = ?
            WHERE job_id = ?
            """,
            (status, chunk_count, file_size, detail, job_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] [_update_job_status]: {e}")


# def _bg_process_file(job_id: str, file_bytes: bytes, filename: str, user_id: int, department: str, permitted_role: str):
#     """
#     Background worker: parse -> chunk -> vectorize -> commit SQLite record.

#     All ChromaDB metadata values are normalised to strings because ChromaDB 0.5.x
#     enforces str/int/float/bool and filters require explicit string comparisons
#     (consistent with RetrievalAgent which always uses str(user_id) in where-clauses).
#     """
#     print(f"[INFO] [BG Worker] Starting ingestion: '{filename}' job={job_id} user={user_id}")
#     try:
#         # Ensure user_id is always a proper integer for SQLite bindings
#         user_id = int(user_id)

#         # Step 1: Hash
#         file_hash = hashlib.sha256(file_bytes).hexdigest()
#         print(f"[INFO] [BG Worker] SHA-256: {file_hash[:12]}... for '{filename}'")

#         # Step 2: Parse & chunk
#         # permitted_role and user_id are forwarded so every chunk is stamped
#         # with the correct user_id (int) and permitted_role for RBAC filtering.
#         try:
#             parser, _, _, _, _ = _get_agents()
#             chunks = parser.parse(
#                 file_bytes,
#                 filename,
#                 user_id=user_id,
#                 department=department,
#                 permitted_role=permitted_role,
#             )
#         except Exception as parse_exc:
#             msg = f"Document parser raised an exception: {parse_exc}"
#             print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")
#             _update_job_status(job_id, "failed", detail=msg)
#             return

#         if not chunks:
#             msg = "No text could be extracted from this file."
#             print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")
#             _update_job_status(job_id, "failed", detail=msg)
#             return

#         print(f"[INFO] [BG Worker] Parsed {len(chunks)} chunks from '{filename}'")

#         # Step 3: Normalise metadata so ChromaDB never rejects the add().
#         # user_id MUST be stored as str to match "$eq": str(user_id) filters
#         # used by RetrievalAgent and the /query endpoint.
#         safe_str_user_id = str(user_id)
#         for c in chunks:
#             m = c["metadata"]
#             m["user_id"]        = safe_str_user_id   # str — consistent with all where-clause filters
#             m["permitted_role"] = str(permitted_role) # ensure RBAC role is always a string
#             m["file_hash"]      = file_hash
#             for k, v in list(m.items()):
#                 if v is None:
#                     m[k] = ""
#                 elif not isinstance(v, (str, int, float, bool)):
#                     m[k] = str(v)

#         # Step 4: Purge stale ChromaDB vectors (deduplication).
#         # Filters use safe_str_user_id (str) to match stored metadata.
#         if collection is not None:
#             try:
#                 collection.delete(
#                     where={
#                         "$and": [
#                             {"user_id":   {"$eq": safe_str_user_id}},
#                             {"file_hash": {"$eq": file_hash}},
#                         ]
#                     }
#                 )
#                 print(f"[INFO] [BG Worker] Purged existing vectors for hash {file_hash[:8]}")
#             except Exception as purge_hash_exc:
#                 print(f"[WARNING] [BG Worker] Hash-based purge skipped ({purge_hash_exc}); trying filename purge")
#                 try:
#                     collection.delete(
#                         where={
#                             "$and": [
#                                 {"user_id":  {"$eq": safe_str_user_id}},
#                                 {"filename": {"$eq": filename}},
#                             ]
#                         }
#                     )
#                 except Exception as purge_name_exc:
#                     print(f"[WARNING] [BG Worker] Filename purge also skipped: {purge_name_exc}")

#         # Step 5: Add to ChromaDB
#         if collection is not None:
#             documents = [c["text"] for c in chunks]
#             metadatas = [c["metadata"] for c in chunks]
#             ids = [f"u{user_id}_{file_hash[:10]}_chunk_{i}" for i in range(len(chunks))]
#             try:
#                 collection.add(documents=documents, metadatas=metadatas, ids=ids)
#                 print(f"[INFO] [BG Worker] Committed {len(chunks)} vectors to ChromaDB for '{filename}'")
#             except Exception as chroma_exc:
#                 msg = f"ChromaDB add() failed: {chroma_exc}"
#                 print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")
#                 _update_job_status(job_id, "failed", detail=msg)
#                 return
#         else:
#             print(f"[WARNING] [BG Worker] ChromaDB unavailable; skipping vector store for '{filename}'")

#         # Step 6: Commit SQLite knowledge_files record with status='Indexed'.
#         # user_id is stored as int (INTEGER column) in SQLite.
#         ext = os.path.splitext(filename.lower())[1]
#         try:
#             conn   = sqlite3.connect(DATABASE_PATH)
#             cursor = conn.cursor()
#             cursor.execute(
#                 "DELETE FROM knowledge_files WHERE user_id = ? AND file_hash = ?",
#                 (user_id, file_hash),
#             )
#             cursor.execute(
#                 """
#                 INSERT INTO knowledge_files
#                     (user_id, filename, file_type, file_size, chunk_count, status, file_hash)
#                 VALUES (?, ?, ?, ?, ?, 'Indexed', ?)
#                 """,
#                 (
#                     user_id,
#                     filename,
#                     ext.lstrip(".").upper(),
#                     len(file_bytes),
#                     len(chunks),
#                     file_hash,
#                 ),
#             )
#             conn.commit()
#             conn.close()
#             print(f"[INFO] [BG Worker] SQLite record committed: '{filename}' status=Indexed user={user_id}")
#         except Exception as db_exc:
#             msg = f"SQLite insert failed: {db_exc}"
#             print(f"[BACKGROUND WORKER ERROR] {filename} (job={job_id}): {msg}")
#             _update_job_status(job_id, "failed", detail=msg)
#             return

#         # Step 7: Mark ingestion job as completed
#         _update_job_status(
#             job_id, "completed",
#             chunk_count=len(chunks),
#             file_size=len(file_bytes),
#             detail=f"Indexed {len(chunks)} chunks (SHA-256: {file_hash[:8]}...)",
#         )
#         print(f"[OK] [BG Worker] '{filename}' (job={job_id}) -> {len(chunks)} chunks indexed for user {user_id}")

#     except Exception as e:
#         import traceback
#         tb = traceback.format_exc()
#         print(f"[BACKGROUND WORKER ERROR] {str(e)}")
#         print(f"[BACKGROUND WORKER ERROR] Full traceback for '{filename}' (job={job_id}):")
#         print(tb)
#         _update_job_status(job_id, "failed", detail=f"Unhandled worker exception: {str(e)}")

def _bg_process_file(job_id: str, file_record_id: int, file_bytes: bytes, filename: str, user_id: int, department: str, permitted_role: str):
    """
    Background worker: parse -> chunk -> vectorize -> update SQLite record.
    """
    print(f"[INFO] [BG Worker] Starting ingestion: '{filename}' job={job_id} user={user_id}")
    try:
        user_id = int(user_id)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Step 1: Parse & chunk
        parser, _, _, _, _ = _get_agents()
        chunks = parser.parse(
            file_bytes,
            filename,
            user_id=user_id,
            department=department,
            permitted_role=permitted_role,
        )

        if not chunks:
            msg = f"No text could be extracted from file '{filename}'."
            print(f"[BG WORKER ERROR] {filename}: {msg}")
            _update_job_status(job_id, "failed", detail=msg)
            _mark_file_status(file_record_id, "Failed")
            return

        # Step 2: Normalise metadata
        safe_str_user_id = str(user_id)
        for c in chunks:
            m = c["metadata"]
            m["user_id"]        = safe_str_user_id
            m["permitted_role"] = str(permitted_role)
            m["file_hash"]      = file_hash
            for k, v in list(m.items()):
                if v is None:
                    m[k] = ""
                elif not isinstance(v, (str, int, float, bool)):
                    m[k] = str(v)

        # Step 3: Add to ChromaDB (upsert handles re-uploads without DuplicateIDException)
        if collection is not None:
            documents = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            ids = [f"u{user_id}_{file_hash[:10]}_chunk_{i}" for i in range(len(chunks))]
            collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        else:
            print(f"[WARNING] [BG Worker] ChromaDB unavailable; skipping vector store for '{filename}'")

        # Step 4: Update SQLite knowledge_files record to 'Indexed'
        conn   = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE knowledge_files
            SET chunk_count = ?, status = 'Indexed', file_hash = ?
            WHERE id = ?
            """,
            (len(chunks), file_hash, file_record_id),
        )
        conn.commit()
        conn.close()

        _update_job_status(
            job_id, "completed",
            chunk_count=len(chunks),
            file_size=len(file_bytes),
            detail=f"Indexed {len(chunks)} chunks",
        )
        print(f"[OK] '{filename}' indexed successfully for user {user_id}")

    except Exception as e:
        import traceback
        print(f"[BG WORKER ERROR] Failed to process {filename} for user_id={user_id}: {str(e)}")
        traceback.print_exc()
        _update_job_status(job_id, "failed", detail=str(e))
        _mark_file_status(file_record_id, "Failed")


def _mark_file_status(file_record_id: int, status: str):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE knowledge_files SET status = ? WHERE id = ?", (status, file_record_id))
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[ERROR] Failed to mark file status: {exc}")


def _log_query_audit(user_id: int, query: str, resolved_query: str, answer: str, confidence_score: int) -> Optional[int]:
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO query_audit_logs
                (user_id, query, resolved_query, answer, confidence_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, query, resolved_query, answer, confidence_score)
        )
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()
        return log_id
    except Exception as e:
        print(f"[WARNING] [_log_query_audit]: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Multi-file authenticated upload (Async Background Tasks) ───────────────
ALLOWED_EXTENSIONS = {".txt", ".csv", ".pdf", ".docx", ".xlsx", ".xls", ".doc", ".png", ".jpg", ".jpeg"}

# @router.post("/upload", status_code=202)
# async def upload_documents(
#     background_tasks: BackgroundTasks,
#     files: List[UploadFile] = File(...),
#     current_user=Depends(get_current_user),
# ):
#     """
#     Accepts one or more files, initializes an ingestion job with status 'processing',
#     schedules async processing in background, and immediately returns 202 Accepted.
#     """
#     dept = getattr(current_user, "department", "General")
#     permitted_role = _role_value(current_user)
#     results = []

#     conn = sqlite3.connect(DATABASE_PATH)
#     cursor = conn.cursor()

#     for file in files:
#         ext = os.path.splitext(file.filename.lower())[1]
#         if ext not in ALLOWED_EXTENSIONS:
#             results.append({
#                 "filename": file.filename,
#                 "status":   "FAILED",
#                 "detail":   f"Unsupported type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
#             })
#             continue

#         try:
#             contents  = await file.read()
#             file_size = len(contents)
#             job_id = uuid.uuid4().hex

#             cursor.execute(
#                 """
#                 INSERT INTO ingestion_jobs
#                     (job_id, user_id, filename, status, chunk_count, file_size, detail)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#                 """,
#                 (job_id, current_user.id, file.filename, "processing", 0, file_size, "Queued for background processing"),
#             )

#             background_tasks.add_task(
#                 _bg_process_file,
#                 job_id,
#                 contents,
#                 file.filename,
#                 current_user.id,
#                 dept,
#                 permitted_role,
#             )

#             results.append({
#                 "job_id":      job_id,
#                 "filename":    file.filename,
#                 "status":      "processing",
#                 "chunk_count": 0,
#                 "file_size":   file_size,
#                 "detail":      "Document queued for background vector indexing."
#             })
#             print(f"🚀 [Async Upload Queued] {file.filename} (Job {job_id}) for user {current_user.id}")

#         except Exception as exc:
#             print(f"[ERROR] [Async Upload Error] {file.filename}: {exc}")
#             results.append({
#                 "filename": file.filename,
#                 "status":   "FAILED",
#                 "detail":   str(exc),
#             })

#     conn.commit()
#     conn.close()

#     primary_job = results[0] if results else {}
#     return JSONResponse(
#         status_code=202,
#         content={
#             "status": "processing",
#             "job_id": primary_job.get("job_id", ""),
#             "filename": primary_job.get("filename", ""),
#             "uploaded": len([r for r in results if r.get("status") == "processing"]),
#             "total_submitted": len(results),
#             "results": results,
#             "detail": "Document ingestion started in background."
#         }
#     )

@router.post("/upload", status_code=202)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user=Depends(get_current_user),
):
    dept = getattr(current_user, "department", "General")
    permitted_role = _role_value(current_user)
    results = []

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    for file in files:
        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": file.filename,
                "status":   "FAILED",
                "detail":   f"Unsupported type: {ext}",
            })
            continue

        try:
            contents  = await file.read()
            file_size = len(contents)
            job_id    = uuid.uuid4().hex

            # 1. Insert into ingestion_jobs
            cursor.execute(
                """
                INSERT INTO ingestion_jobs
                    (job_id, user_id, filename, status, chunk_count, file_size, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, current_user.id, file.filename, "processing", 0, file_size, "Queued for processing"),
            )

            # 2. Insert IMMEDIATELY into knowledge_files so GET /files returns it right away
            cursor.execute(
                """
                INSERT INTO knowledge_files
                    (user_id, filename, file_type, file_size, chunk_count, status, file_hash)
                VALUES (?, ?, ?, ?, 0, 'Processing', '')
                """,
                (current_user.id, file.filename, ext.lstrip(".").upper(), file_size),
            )
            file_record_id = cursor.lastrowid

            background_tasks.add_task(
                _bg_process_file,
                job_id,
                file_record_id,
                contents,
                file.filename,
                current_user.id,
                dept,
                permitted_role,
            )

            results.append({
                "job_id":      job_id,
                "filename":    file.filename,
                "status":      "processing",
                "chunk_count": 0,
                "file_size":   file_size,
                "detail":      "Document queued for background vector indexing."
            })

        except Exception as exc:
            print(f"[ERROR] [Upload Error] {file.filename}: {exc}")
            results.append({"filename": file.filename, "status": "FAILED", "detail": str(exc)})

    conn.commit()
    conn.close()

    primary_job = results[0] if results else {}
    return JSONResponse(
        status_code=202,
        content={
            "status": "processing",
            "job_id": primary_job.get("job_id", ""),
            "filename": primary_job.get("filename", ""),
            "uploaded": len([r for r in results if r.get("status") == "processing"]),
            "total_submitted": len(results),
            "results": results,
            "detail": "Document ingestion started in background."
        }
    )

# ── 1b. Polling Endpoint for Ingestion Job Progress ────────────────────────────
@router.get("/ingest-status/{job_id}")
async def get_ingest_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """
    Returns job status ('processing', 'completed', 'failed') and chunk count for an upload job.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM ingestion_jobs WHERE job_id = ? AND user_id = ?",
            (job_id, current_user.id),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Ingestion job not found.")

        job_dict = dict(row)
        return {
            "job_id": job_dict["job_id"],
            "filename": job_dict["filename"],
            "status": job_dict["status"],
            "chunk_count": job_dict["chunk_count"],
            "file_size": job_dict["file_size"],
            "detail": job_dict.get("detail", ""),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch job status: {exc}")


# ── 2. List user-scoped knowledge files ───────────────────────────────────────
@router.get("/files")
async def list_knowledge_files(current_user=Depends(get_current_user)):
    """Returns all uploaded files belonging to the current user."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM knowledge_files WHERE user_id = ? ORDER BY id DESC",
            (current_user.id,),
        )
        rows  = cursor.fetchall()
        files = [dict(r) for r in rows]
        conn.close()
        # print(f"[DEBUG GET FILES] DB Path: {DATABASE_PATH} | Total rows for user {current_user.id}: {len(files)}")
        return files
    except Exception as exc:
        # print(f"[ERROR GET FILES] {exc}")
        return []


# ── 3. Delete file + purge ChromaDB chunks ────────────────────────────────────
@router.delete("/files/{file_id}")
async def delete_knowledge_file(file_id: int, current_user=Depends(get_current_user)):
    """
    Deletes a file record from knowledge_files and purges all related ChromaDB
    chunks that are scoped to this user and filename.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute(
            "SELECT * FROM knowledge_files WHERE id = ? AND user_id = ?",
            (file_id, current_user.id),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(
                status_code=404, detail="File not found or access denied."
            )

        filename = row["filename"]

        # Purge ChromaDB chunks for this user + filename.
        # user_id filter uses str(current_user.id) to match how vectors are stored.
        try:
            existing = collection.get(
                where={
                    "$and": [
                        {"user_id":  {"$eq": str(current_user.id)}},
                        {"filename": {"$eq": filename}},
                    ]
                }
            )
            chunk_ids = existing.get("ids", [])
            if chunk_ids:
                collection.delete(ids=chunk_ids)
                print(f"🗑️  [Delete] Purged {len(chunk_ids)} chunks for {filename} (user {current_user.id})")
        except Exception as chroma_exc:
            print(f"[WARNING]  [Delete] ChromaDB purge partial failure: {chroma_exc}")

        # Remove DB record
        cursor.execute(
            "DELETE FROM knowledge_files WHERE id = ? AND user_id = ?",
            (file_id, current_user.id),
        )
        conn.commit()
        conn.close()

        return {
            "status":   "SUCCESS",
            "detail":   f"'{filename}' has been deleted from your knowledge base.",
            "filename": filename,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(exc)}")


# ── 4. Knowledge articles (runbooks) ──────────────────────────────────────────
@router.get("/articles")
async def list_knowledge_articles(current_user=Depends(get_current_user)):
    """Returns knowledge articles owned by the current user from the database."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM knowledge_articles WHERE user_id = ? ORDER BY id DESC",
            (current_user.id,),
        )
        rows     = cursor.fetchall()
        articles = [dict(r) for r in rows]
        conn.close()
        # Return both 'articles' and 'files' keys for complete frontend backwards compatibility
        return {"status": "SUCCESS", "articles": articles, "files": articles, "total_documents": len(articles)}
    except Exception as exc:
        return {"status": "FAILED", "articles": [], "files": [], "detail": str(exc)}


@router.post("/articles")
async def create_knowledge_article(
    payload: ArticleCreateRequest, current_user=Depends(get_current_user)
):
    """Saves a new knowledge article/runbook scoped to the current user and indexes it in ChromaDB."""
    try:
        conn   = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge_articles (user_id, title, category, author, content) VALUES (?, ?, ?, ?, ?)",
            (current_user.id, payload.title, payload.category.upper(), payload.author or getattr(current_user, 'email', 'Admin'), payload.content),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        # Vectorize article content into ChromaDB for RAG search.
        # user_id stored as str to be consistent with file chunk metadata.
        if collection is not None and payload.content:
            try:
                doc_id = f"article_u{current_user.id}_{new_id}"
                collection.add(
                    documents=[f"Title: {payload.title}\nCategory: {payload.category}\nContent: {payload.content}"],
                    metadatas=[{
                        "user_id": str(current_user.id),
                        "filename": f"Article #{new_id}: {payload.title}",
                        "source": "Article",
                        "category": payload.category.upper(),
                        "permitted_role": _role_value(current_user),
                    }],
                    ids=[doc_id]
                )
            except Exception as vector_err:
                print(f"[WARNING] Article vector indexing error: {vector_err}")

        return {
            "status":   "SUCCESS",
            "id":       new_id,
            "title":    payload.title,
            "category": payload.category.upper(),
            "author":   payload.author,
            "content":  payload.content,
            "detail":   "Article saved to your knowledge base.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save article: {str(exc)}")


@router.delete("/articles/{article_id}")
async def delete_knowledge_article(article_id: int, current_user=Depends(get_current_user)):
    """Deletes a knowledge article from database and purges its ChromaDB vector record."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM knowledge_articles WHERE id = ? AND user_id = ?", (article_id, current_user.id))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Article not found or access denied.")

        cursor.execute("DELETE FROM knowledge_articles WHERE id = ? AND user_id = ?", (article_id, current_user.id))
        conn.commit()
        conn.close()

        if collection is not None:
            try:
                collection.delete(ids=[f"article_u{current_user.id}_{article_id}"])
            except Exception:
                pass

        return {"status": "SUCCESS", "id": article_id, "detail": "Article deleted successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete article: {str(exc)}")


# ── 5. Legacy single-pass RAG query (no auth, backward compatible) ─────────────
@router.post("/query", response_model=RAGQueryResponse)
async def query_knowledge_base(payload: RAGQueryRequest, current_user=Depends(get_current_user)):
    try:
        user_question = payload.question

        # Intent routing
        try:
            intent_pass = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict internal traffic router. Classify the user input into exactly one of two tags: "
                            "'COMPLIANCE_QUERY' or 'GENERAL_CHATTER'. Respond with ONLY the uppercase tag name."
                        ),
                    },
                    {"role": "user", "content": user_question},
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0,
            )
            intent = intent_pass.choices[0].message.content.strip()
        except Exception:
            intent = "COMPLIANCE_QUERY"

        if "GENERAL_CHATTER" in intent:
            chatter = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful enterprise compliance assistant."},
                    {"role": "user", "content": user_question},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.6,
            )
            return RAGQueryResponse(
                status="SUCCESS",
                message=chatter.choices[0].message.content,
                citation="System Diagnostics (No File Accessed)",
            )

        if collection is None:
            return RAGQueryResponse(
                status="SUCCESS",
                message="No documents found in your knowledge base. Please upload documents first.",
                citation="None",
            )

        user_role = _role_value(current_user)
        # user_id must be str to match ChromaDB metadata stored as str(user_id)
        where_filter = {
            "$and": [
                {"permitted_role": user_role},
                {"user_id": str(current_user.id)},
            ]
        }
        results = collection.query(query_texts=[user_question], n_results=3, where=where_filter)
        if not results or not results.get("documents") or len(results["documents"][0]) == 0:
            return RAGQueryResponse(
                status="SUCCESS",
                message="No documents found in your knowledge base for this query.",
                citation="None",
            )

        context_block = ""
        citations     = set()
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            context_block += f"- {doc}\n"
            citations.add(meta.get("source", "Unknown Document"))

        system_instruction = (
            "You are an expert infrastructure compliance analyst. Answer the user's question "
            "using ONLY the source context below. Keep responses professional and structured.\n\n"
            f"--- SOURCE CONTEXT ---\n{context_block}--- END CONTEXT ---"
        )

        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user",   "content": user_question},
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.2,
            )
            synthesized_answer = chat_completion.choices[0].message.content
        except Exception as groq_error:
            raise HTTPException(
                status_code=503,
                detail="Cloud inference engine temporarily unavailable. Please retry.",
            )

        return RAGQueryResponse(
            status="SUCCESS",
            message=synthesized_answer,
            citation=", ".join(list(citations)),
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query engine failure: {str(exc)}")


# ── 6. Multi-agent pipeline query ─────────────────────────────────────────────
@router.post("/agent-query")
async def agent_query(
    payload: AgentQueryRequest,
    current_user=Depends(get_current_user),
):
    """
    Full multi-agent RAG pipeline:
      Planner → Hybrid Retrieval → Groq Synthesis → Verification → Report Format

    Returns structured JSON with answer, citations, confidence, and execution plan.
    """
    parser, retriever, planner, verifier, reporter = _get_agents()
    query = payload.question

    # ── Step 1: Planner — classify intent & decompose ─────────────────────────
    print(f"[INFO] [AgentQuery] Step 1: Planning query for user {current_user.id}")
    chat_hist = [m.model_dump() if hasattr(m, "model_dump") else m.dict() for m in (payload.chat_history or [])]
    plan = planner.plan(query, chat_history=chat_hist)

    # ── CHITCHAT fast-path: bypass all retrieval & verification ───────────────
    if plan.get("intent") == "CHITCHAT":
        print(f"[INFO] [AgentQuery] CHITCHAT fast-path activated.")
        chitchat_answer = (
            "Hello! I am your GuardCore Enterprise Assistant. "
            "How can I help you analyze your enterprise documents, "
            "telemetry logs, or incident reports today?"
        )
        log_id = _log_query_audit(
            user_id=current_user.id,
            query=query,
            resolved_query=query,
            answer=chitchat_answer,
            confidence_score=100,
        )
        return {
            "status":           "SUCCESS",
            "log_id":           log_id,
            "answer":           chitchat_answer,
            "citations":        [],
            "confidence_score": 100,
            "is_grounded":      True,
            "execution_plan":   plan.get("execution_plan", ""),
            "sub_queries":      [],
            "resolved_query":   query,
            "report":           "",
        }

    resolved_query = plan.get("resolved_query", query)
    sub_queries    = plan.get("sub_queries", [resolved_query])
    execution_plan = plan.get("execution_plan", "Direct retrieval.")

    # ── Step 2: Hybrid Retrieval for each sub-query ──────────────────────────
    print(f"[INFO] [AgentQuery] Step 2: Hybrid retrieval across {len(sub_queries)} sub-queries")
    all_chunks = []
    seen_texts = set()
    user_dept  = getattr(current_user, "department", "General")
    user_role  = _role_value(current_user)
    meta_filter = plan.get("metadata_filter")
    for sq in sub_queries:
        chunks = retriever.search(
            sq,
            user_id=current_user.id,
            user_department=user_dept,
            user_role=user_role,
            n_results=5,
            metadata_filter=meta_filter,
        )
        for c in chunks:
            if c["text"] not in seen_texts:
                all_chunks.append(c)
                seen_texts.add(c["text"])

    if not all_chunks:
        return {
            "status":           "SUCCESS",
            "answer":           "[WARNING] No relevant documents found in your knowledge base. Please upload documents first.",
            "citations":        [],
            "confidence_score": 0,
            "execution_plan":   execution_plan,
            "resolved_query":   resolved_query,
            "is_grounded":      False,
        }

    # ── Step 3: Synthesize answer via Groq ─────────────────────────────────
    print(f"[INFO] [AgentQuery] Step 3: Synthesizing answer from {len(all_chunks)} chunks")
    context_block = "\n\n".join(
        [f"[Source: {c['metadata'].get('filename','?')}, Page: {c['metadata'].get('page','?')}]\n{c['text']}"
         for c in all_chunks[:8]]
    )
    system_prompt = (
        "You are a senior enterprise intelligence analyst at GuardCore. "
        "Answer the user's question using ONLY the enterprise document context provided below. "
        "Be thorough, structured, and professional. Use bullet points and headers where relevant. "
        "If the context is insufficient, clearly state what information is missing.\n\n"
        f"=== ENTERPRISE DOCUMENT CONTEXT ===\n{context_block}\n=== END CONTEXT ==="
    )
    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": resolved_query},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.15,
        )
        raw_answer = completion.choices[0].message.content
    except Exception as groq_exc:
        print(f"[ERROR] [AgentQuery] Groq synthesis failed: {groq_exc}")
        raw_answer = "Unable to synthesize answer — inference engine temporarily unavailable."

    # ── Step 4: Verification ─────────────────────────────────────────────────────
    print(f"[OK] [AgentQuery] Step 4: Verifying groundedness")
    verification = verifier.verify(raw_answer, all_chunks)

    # ── Step 5: Report format ─────────────────────────────────────────────────
    report = reporter.format(
        query      = resolved_query,
        answer     = verification["verified_answer"],
        citations  = verification["citations"],
        confidence = verification["confidence_score"],
    )

    # ── Step 6: Query audit log recording ────────────────────────────────────
    log_id = _log_query_audit(
        user_id=current_user.id,
        query=query,
        resolved_query=resolved_query,
        answer=verification["verified_answer"],
        confidence_score=verification["confidence_score"],
    )

    return {
        "status":           "SUCCESS",
        "log_id":           log_id,
        "answer":           verification["verified_answer"],
        "citations":        verification["citations"],
        "confidence_score": verification["confidence_score"],
        "is_grounded":      verification["is_grounded"],
        "execution_plan":   execution_plan,
        "sub_queries":      sub_queries,
        "resolved_query":   resolved_query,
        "report":           report,
    }


# ── 7. Feedback Endpoint (Thumbs Up / Thumbs Down) ────────────────────────────
@router.post("/feedback")
async def submit_query_feedback(
    payload: FeedbackRequest,
    current_user=Depends(get_current_user),
):
    """
    Records user rating (+1 thumbs up or -1 thumbs down) for a specific query log entry.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE query_audit_logs SET rating = ? WHERE id = ? AND user_id = ?",
            (payload.rating, payload.log_id, current_user.id),
        )
        conn.commit()
        conn.close()
        return {
            "status": "SUCCESS",
            "log_id": payload.log_id,
            "rating": payload.rating,
            "detail": "Feedback recorded successfully."
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {exc}")


# ── 8. Chat History (Query Audit Log) ─────────────────────────────────────────
@router.get("/history")
async def get_chat_history(current_user=Depends(get_current_user)):
    """
    Returns the authenticated user's query audit log sessions ordered most-recent-first.
    Each session contains: id, query, answer, confidence_score, rating, created_at.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, query, answer, confidence_score, rating, created_at
            FROM query_audit_logs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (current_user.id,),
        )
        rows = cursor.fetchall()
        sessions = [dict(r) for r in rows]
        conn.close()
        return {
            "status": "SUCCESS",
            "sessions": sessions,
            "total": len(sessions),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(exc)}")


@router.delete("/history/{log_id}")
async def delete_chat_session(log_id: int, current_user=Depends(get_current_user)):
    """
    Deletes a specific query audit log entry (chat session) belonging to the authenticated user.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        # Verify ownership before deleting
        cursor.execute(
            "SELECT id FROM query_audit_logs WHERE id = ? AND user_id = ?",
            (log_id, current_user.id),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found or access denied.")

        cursor.execute(
            "DELETE FROM query_audit_logs WHERE id = ? AND user_id = ?",
            (log_id, current_user.id),
        )
        conn.commit()
        conn.close()
        return {
            "status": "SUCCESS",
            "detail": f"Chat session #{log_id} deleted.",
            "id": log_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(exc)}")
