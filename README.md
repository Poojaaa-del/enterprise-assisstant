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


## Contributing
Contributions are welcome. Please open issues and PRs for feature work, bugfixes, and documentation improvements. When contributing, avoid committing secrets and ensure linting/tests pass.


## License
MIT License

Copyright (c) 2026 Pooja Kumari

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


---
