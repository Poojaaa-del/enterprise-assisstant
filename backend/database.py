# backend/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Configurable database URL via environment variable with local fallback
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = str(BASE_DIR / "triage.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# SQLite requires check_same_thread=False for multi-threaded access in FastAPI
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding database sessions to endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def patch_database_schema():
    """Ensures compliance_logs has the required file_content schema update dynamically."""
    inspector = inspect(engine)
    if "compliance_logs" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("compliance_logs")]
        if "file_content" not in columns:
            print("[WARNING] [Migration Hub] Legacy database table detected. Injecting file_content text column...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE compliance_logs ADD COLUMN file_content TEXT"))
            print("[OK] [Migration Hub] Table compliance_logs updated successfully.")


def patch_user_id_column():
    """Adds user_id column to compliance_logs for multi-tenant data isolation."""
    inspector = inspect(engine)
    if "compliance_logs" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("compliance_logs")]
        if "user_id" not in columns:
            print("[WARNING] [Migration Hub] Adding user_id column to compliance_logs for tenant isolation...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE compliance_logs ADD COLUMN user_id INTEGER"))
            print("[OK] [Migration Hub] user_id column added to compliance_logs.")


def patch_knowledge_articles_table():
    """Creates the knowledge_articles table for per-user runbook storage if it doesn't exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT DEFAULT 'RUNBOOK',
                author TEXT,
                content TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
    print("[OK] [Migration Hub] knowledge_articles table ensured.")


def patch_knowledge_files_table():
    """Creates the knowledge_files table for tracking uploaded documents per user.

    Schema is kept in sync with knowledge.py _init_db_tables() and the
    _bg_process_file INSERT which references all these columns (including file_hash).
    """
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Indexed',
                file_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    print("[OK] [Migration Hub] knowledge_files table ensured.")


def patch_ingestion_jobs_table():
    """Creates the ingestion_jobs table for asynchronous document processing status polling."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                status TEXT DEFAULT 'processing',
                chunk_count INTEGER DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                detail TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
    print("[OK] [Migration Hub] ingestion_jobs table ensured.")


def patch_query_audit_log_table():
    """Creates the query_audit_logs table for logging agent queries and user feedback ratings."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS query_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                resolved_query TEXT,
                answer TEXT,
                confidence_score INTEGER DEFAULT 0,
                rating INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """))
    print("[OK] [Migration Hub] query_audit_logs table ensured.")


def patch_user_department_column():
    """Ensures users table has department column for RBAC scoping."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "department" not in columns:
            print("[WARNING] [Migration Hub] Adding department column to users table for RBAC department scoping...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'General'"))
            print("[OK] [Migration Hub] department column added to users table.")


def patch_user_profile_columns():
    """Ensures users table has all profile metadata columns (avatar_color, created_at, full_name)."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        with engine.begin() as conn:
            if "avatar_color" not in columns:
                print("[WARNING] [Migration Hub] Adding avatar_color column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN avatar_color TEXT DEFAULT 'from-cyan-500 to-blue-600'"))
                print("[OK] [Migration Hub] avatar_color column added to users table.")
            if "full_name" not in columns:
                print("[WARNING] [Migration Hub] Adding full_name column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN full_name TEXT"))
                print("[OK] [Migration Hub] full_name column added to users table.")
            if "created_at" not in columns:
                print("[WARNING] [Migration Hub] Adding created_at column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP"))
                print("[OK] [Migration Hub] created_at column added to users table.")


def patch_user_verification_column():
    """Ensures users table has is_verified for email verification login gating."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "is_verified" not in columns:
            print("[WARNING] [Migration Hub] Adding is_verified column to users table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0"))
            print("[OK] [Migration Hub] is_verified column added to users table.")


def patch_knowledge_files_hash_column():
    """Ensures knowledge_files table has file_hash column for SHA-256 deduplication."""
    inspector = inspect(engine)
    if "knowledge_files" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("knowledge_files")]
        if "file_hash" not in columns:
            print("[WARNING] [Migration Hub] Adding file_hash column to knowledge_files table...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE knowledge_files ADD COLUMN file_hash TEXT"))
            print("[OK] [Migration Hub] file_hash column added to knowledge_files table.")
