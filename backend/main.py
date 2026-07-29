import os
import sys
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (), {"__version__": getattr(bcrypt, "__version__", "4.0.1")})
# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError from any
# remaining non-ASCII characters in log messages (cp1252 console default).
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Text
from dotenv import load_dotenv

# ─── DATABASE & MODELS ──────────────────────────────────────────────
# Shared database session and migration patch from database.py
from database import (
    Base,
    engine,
    patch_database_schema,
    patch_user_id_column,
    patch_knowledge_articles_table,
    patch_knowledge_files_table,
    patch_ingestion_jobs_table,
    patch_query_audit_log_table,
    patch_user_department_column,
    patch_user_profile_columns,
    patch_user_verification_column,
    patch_knowledge_files_hash_column,
)

# Explicitly import User model so SQLAlchemy registers the 'users' table
from models.user import User

# ─── ROUTER IMPORTS ────────────────────────────────────────────────
from api.knowledge import router as knowledge_router
from api.triage import router as triage_router
from api.auth import router as auth_router
from api.reports import router as reports_router
from api.user import router as user_router

# Load environment configurations
load_dotenv()

# ─── DATABASE MODELS ───────────────────────────────────────────────
class ComplianceLog(Base):
    __tablename__ = "compliance_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    file_name = Column(String)
    file_content = Column(Text, nullable=True)
    status = Column(String)
    jira_key = Column(String)
    slack_status = Column(String)


# ─── INITIALIZE DATABASE SCHEMA & MIGRATIONS ───────────────────────
# 1. Run dynamic schema patch for legacy compliance logs
try:
    patch_database_schema()
except Exception as e:
    print(f"[WARNING] [Migration Warning] Schema patch bypass: {e}")

# 2. Automatically create all missing tables ('users', 'compliance_logs', etc.)
Base.metadata.create_all(bind=engine)

# 3. Add user_id column to compliance_logs for multi-tenant isolation
try:
    patch_user_id_column()
except Exception as e:
    print(f"[WARNING] [Migration Warning] user_id patch bypass: {e}")

# 4. Ensure knowledge_articles table exists for per-user runbook storage
try:
    patch_knowledge_articles_table()
except Exception as e:
    print(f"[WARNING] [Migration Warning] knowledge_articles table patch bypass: {e}")

# 5. Ensure knowledge_files table exists for per-user file tracking
try:
    patch_knowledge_files_table()
except Exception as e:
    print(f"[WARNING] [Migration Warning] knowledge_files table patch bypass: {e}")

# 6. Ensure ingestion_jobs table exists for async upload status polling
try:
    patch_ingestion_jobs_table()
except Exception as e:
    print(f"[WARNING] [Migration Warning] ingestion_jobs table patch bypass: {e}")

# 7. Ensure query_audit_logs table exists for audit trail & feedback
try:
    patch_query_audit_log_table()
except Exception as e:
    print(f"[WARNING] [Migration Warning] query_audit_logs table patch bypass: {e}")

# 8. Ensure department column exists in users table for RBAC scoping
try:
    patch_user_department_column()
except Exception as e:
    print(f"[WARNING] [Migration Warning] user department patch bypass: {e}")

# 9. Ensure profile metadata columns (avatar_color, full_name, created_at) exist in users table
try:
    patch_user_profile_columns()
except Exception as e:
    print(f"[WARNING] [Migration Warning] user profile columns patch bypass: {e}")

# 10. Ensure is_verified column exists in users table for email verification
try:
    patch_user_verification_column()
except Exception as e:
    print(f"[WARNING] [Migration Warning] user verification patch bypass: {e}")

# 11. Ensure file_hash column exists in knowledge_files table for SHA-256 deduplication
try:
    patch_knowledge_files_hash_column()
except Exception as e:
    print(f"[WARNING] [Migration Warning] file_hash patch bypass: {e}")


# ─── GLOBAL CONVERSATION & AGENT MEMORY STORE ─────────────────────
CONVERSATION_MEMORY: List[Dict[str, Any]] = []


# ─── FASTAPI APPLICATION INSTANTIATION ─────────────────────────────
app = FastAPI(
    title="EMKA Enterprise Control Core",
    description="Autonomous Intelligence Engine & System Triage Control Hub",
    version="1.0.0",
)

ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to ["*"] in development to avoid CORS issues across containers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect modular feature routers
app.include_router(knowledge_router)
app.include_router(triage_router)
app.include_router(auth_router)
app.include_router(reports_router)
app.include_router(user_router)


# ─── CORE SYSTEM ENDPOINTS ─────────────────────────────────────────

@app.get("/")
def health_check():
    return {
        "status": "ONLINE",
        "matrix": "EMKA Infrastructure Operations Active",
        "memory_buffer_count": len(CONVERSATION_MEMORY),
    }


@app.post("/api/v1/conversation-history/clear")
async def clear_conversation_history():
    """Clears active conversation/chat memory state across agent workflows."""
    global CONVERSATION_MEMORY
    try:
        CONVERSATION_MEMORY.clear()
        return {
            "status": "SUCCESS",
            "message": "Conversation history and agent memory successfully wiped.",
            "active_memory_count": len(CONVERSATION_MEMORY),
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Failed to clear conversation history: {str(e)}",
        }
