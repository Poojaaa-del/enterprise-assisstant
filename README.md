# LogTriage AI — Multi-Agent RAG & System Incident Triage Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/) [![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react)](https://reactjs.org/) [![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/) [![ChromaDB](https://img.shields.io/badge/ChromaDB-000000?style=flat-square)](https://www.trychroma.com/) [![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-38B2AC?style=flat-square&logo=tailwindcss)](https://tailwindcss.com/) [![Render](https://img.shields.io/badge/Render-deployed-ff6b6b?style=flat-square)](https://render.com/) [![Vercel](https://img.shields.io/badge/Vercel-deployed-000000?style=flat-square)](https://vercel.com/) [![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)


## Project Overview
LogTriage AI automates raw stack trace triage and runbook Q&A so DevOps and SRE teams can drastically reduce Mean Time to Resolution (MTTR). It combines multi-agent planning, hybrid retrieval (vector + BM25), and grounded answer verification over your team's documentation.


## System Architecture (ASCII Flowchart)

React Frontend (Vercel)
  |
  v
FastAPI Backend (Render)
  |
  v
Planner Agent
  |
  v
ChromaDB + BM25 Hybrid Retrieval
  |
  v
Reporter Agent
  |
  v
Grounded Answer

ASCII (compact view):

[React Frontend (Vercel)] --> [FastAPI Backend (Render)] --> [Planner Agent]
                                                            |
                                                            v
[Grounded Answer] <-- [Reporter Agent] <-- [ChromaDB + BM25 Hybrid Retrieval]


## Key Features
- 🚨 Automated Incident Triage: Instant risk classification (`LOW_PRIORITY` vs. `MANDATORY`) for raw stack traces.
- 🔍 Multi-Agent RAG Engine: Coordinated sub-query planning, hybrid vector search, and answer verification over uploaded PDFs/runbooks.
- ⚡ Production-Optimized: Custom memory management, query expansion throttling, and explicit garbage collection tuned for small Render instances (512 MB).
- 🔒 Enterprise Security: JWT authentication with tenant data isolation and per-tenant data boundaries.


## Tech Stack
| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Lucide Icons |
| Backend | FastAPI, Uvicorn, Python 3.11+, SQLite / Postgres (configurable) |
| AI / RAG Engine | Groq (optional), OpenAI-compatible models, BM25 (Whoosh / rank-bm25), ChromaDB vectors |
| Infrastructure | Render (backend), Vercel (frontend), Docker, GitHub Actions (CI) |


## Local Development Quickstart
Prerequisites: Python 3.11+, Node.js (16+), npm or yarn, Docker (optional)

1. Clone the repository

   git clone <your-repo-url>
   cd enterprise-assistant

2. Backend (Python)

   - Create a virtual environment and install dependencies:

     python -m venv .venv
     .\.venv\Scripts\activate   # Windows
     pip install --upgrade pip
     pip install -r backend/requirements.txt

   - Copy the environment template and populate secrets (do NOT commit):

     copy .env.production.template .env
     # Edit .env and provide real values for OPENAI_API_KEY, GROQ_API_KEY, JWT_SECRET, DATABASE_URL, etc.

   - Run the backend server (development):

     cd backend
     uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

3. Frontend (React + Vite)

   - Install dependencies and run dev server:

     cd frontend
     npm install
     npm run dev

   - The frontend typically runs at http://localhost:5173 and will call the backend API at the configured VITE_API_URL / REACT_APP_API_URL.


## Environment Variables Reference
Create an `.env` file in the repository root or backend folder and set the following values (example placeholders shown):

- OPENAI_API_KEY=sk_your_openai_key_here
- GROQ_API_KEY=gsk_your_groq_api_key_here
- JWT_SECRET=your_jwt_secret_here_min_length_32
- DATABASE_URL=postgresql://user:password@localhost:5432/triage_db
- REACT_APP_API_URL=http://localhost:8000
- VITE_API_URL=http://localhost:8000
- MAX_SUB_QUERIES=1

Notes:
- Never commit real secrets or API keys. Use environment variables or a secrets manager in production.
- MAX_SUB_QUERIES controls planner decomposition (set to 1 to avoid memory spikes on constrained hosts).


## Security & Pre-Flight Audit (Summary)
The repository was scanned for common pitfalls before public release:

1. .gitignore checks
   - Confirmed patterns exist to ignore local environment and build artifacts. Recommended entries (and currently present) include:
     - `.env`, `*.env`, `backend/.env`, `frontend/.env`, `.env.local`, `.env.*.local` (if you use them locally)
     - `node_modules/`, `frontend/node_modules/`, `dist/`, `build/`
     - `chroma/`, `chroma_db/`, `*.sqlite3`, `*.db`, `triage.db`
     - `__pycache__/`, `*.pyc`

2. Hardcoded secrets scan
   - All code files were scanned for obvious hardcoded API keys (patterns like `sk-`, `gsk_`, `AIza`, `AKIA`). No active production keys were found in tracked source files. A `.env.production.template` contains placeholder values — this is intended and safe.
   - A few log files may contain provider identifiers or org ids in logs; these are not secret credentials but should be excluded from public repos if they contain sensitive telemetry.

3. Recommendations before publishing
   - Ensure `.env` and any `.pem`, `.p12`, or credentials JSON files are NOT committed. Keep them in the environment or a secrets manager.
   - Replace `.env.production.template` placeholder keys with environment variables at deploy time.
   - Remove or rotate any real keys that may have been used during development and accidentally leaked.
   - Consider adding a pre-commit hook (e.g., detect-secrets or git-secrets) to avoid committing tokens.
   - Add a SECURITY.md with disclosure and reporting guidelines for your project.


## Contributing
Contributions are welcome. Please open issues and PRs for feature work, bugfixes, and documentation improvements. When contributing, avoid committing secrets and ensure linting/tests pass.


## License
Specify your license here (e.g., MIT). Replace this section with an appropriate license file.


---

If you'd like, I can:
- Commit README.md to the repo and add a short commit message.
- Add the recommended `.gitignore` improvements automatically.
- Run another secret-scan pass and produce a short report of any files that contain high-entropy strings that look like secrets.

Tell me which follow-ups to run next.