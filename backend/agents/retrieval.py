# backend/agents/retrieval.py
"""
RetrievalAgent — Hybrid Retrieval (ChromaDB vector + BM25 keyword)
All queries are scoped to a specific user_id via ChromaDB metadata filters.
"""
import os
import math
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi


class RetrievalAgent:
    def __init__(self):
        BASE_DIR   = os.path.dirname(os.path.dirname(__file__))
        CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

        self.embedding_engine = embedding_functions.HuggingFaceEmbeddingFunction(
        api_key=os.environ.get("HF_TOKEN"),
        model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection    = self.chroma_client.get_or_create_collection(
            name="guard_core_nodes",
            embedding_function=self.embedding_engine,
        )

    # ── Legacy compatibility method (used by triage.py / PlannerAgent) ──────
    def extract_compliance_context(self, planner_analysis: dict) -> tuple:
        """
        Executes vector similarity queries for incident triage (no user scoping).
        Kept for backward compatibility with the existing triage pipeline.
        """
        search_vector = planner_analysis.get(
            "security_anomaly_summary", "infrastructure compliance risk"
        )
        try:
            results = self.collection.query(
                query_texts=[search_vector],
                n_results=2,
            )
            if not results or not results.get("documents") or len(results["documents"][0]) == 0:
                return (
                    "No explicit regulatory rules found matching this query in the current vector space index.",
                    "None",
                )
            matched_documents = results["documents"][0]
            matched_metadatas = results["metadatas"][0]
            context_payload   = "\n".join([f"- {doc}" for doc in matched_documents])
            source_citations  = set()
            for meta in matched_metadatas:
                source_citations.add(meta.get("source", "Unknown Registry Node"))
            return context_payload, ", ".join(list(source_citations))
        except Exception as e:
            print(f"[ERROR] [Agent Matrix Failure - Retrieval]: {str(e)}")
            return "Internal data layer retrieval trace exception encountered.", "None"

    # ── Primary hybrid retrieval method (new multi-agent pipeline) ───────────
    def search(
        self,
        query: str,
        user_id: int,
        user_department: Optional[str] = "General",
        user_role: str = "USER",
        n_results: int = 8,
        metadata_filter: Optional[dict] = None,
    ) -> List[dict]:
        """
        Performs hybrid retrieval:
          1. ChromaDB vector search filtered to user/department + optional metadata_filter (e.g. date)
          2. BM25 keyword re-rank over candidate chunks
          3. Reciprocal Rank Fusion (RRF) merge → top-K chunks returned
        """
        # ── Step 1: Vector retrieval with user/department scoped filter ──────
        # user_id stored as str in ChromaDB metadata (normalised by _bg_process_file).
        # The where-clause MUST use str(user_id) for the $eq comparison to match.
        str_user_id = str(user_id)
        where_filter = {
            "$and": [
                {"permitted_role": user_role},
                {"user_id": str_user_id},
            ]
        }

        # Combine with temporal date metadata filter if present
        if metadata_filter and "date" in metadata_filter:
            date_val = metadata_filter["date"]
            where_filter = {
                "$and": [
                    where_filter,
                    {"date": {"$eq": date_val}}
                ]
            }

        # Primary query: scoped by both permitted_role and user_id
        try:
            vec_results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results * 3, 50),   # over-fetch for re-ranking
                where=where_filter,
            )
        except Exception as exc:
            print(f"[WARNING] [RetrievalAgent] Primary query failed ({exc}); trying user_id fallback.")
            vec_results = None

        # Fallback: if primary returned 0 docs (e.g. permitted_role mismatch),
        # retry with only user_id so the user's uploaded documents are still found.
        docs = vec_results.get("documents", [[]])[0] if vec_results else []
        if not docs:
            try:
                vec_results = self.collection.query(
                    query_texts=[query],
                    n_results=min(n_results * 3, 50),
                    where={"user_id": str_user_id},
                )
            except Exception as fallback_exc:
                print(f"[ERROR] [RetrievalAgent] ChromaDB fallback query also failed: {fallback_exc}")
                return []

        # Extract results from whichever query (primary or fallback) produced data
        docs      = vec_results.get("documents",  [[]])[0] if vec_results else []
        metas     = vec_results.get("metadatas",  [[]])[0] if vec_results else []
        distances = vec_results.get("distances",  [[]])[0] if vec_results else []

        if not docs:
            return []

        # ── Step 2: BM25 keyword search over the candidates ──────────────────
        tokenised_docs = [d.lower().split() for d in docs]
        bm25           = BM25Okapi(tokenised_docs)
        bm25_scores    = bm25.get_scores(query.lower().split())

        # ── Step 3: Reciprocal Rank Fusion (RRF, k=60) ───────────────────────
        K = 60
        # Vector rank (ascending distance = higher rank)
        vec_ranks  = {i: rank + 1 for rank, i in enumerate(range(len(docs)))}
        # BM25 rank (descending score = higher rank)
        bm25_ranks = {
            i: rank + 1
            for rank, i in enumerate(
                sorted(range(len(docs)), key=lambda x: bm25_scores[x], reverse=True)
            )
        }

        rrf_scores = {
            i: (1.0 / (K + vec_ranks[i])) + (1.0 / (K + bm25_ranks[i]))
            for i in range(len(docs))
        }

        # Sort by RRF score descending and take top n_results
        ranked_indices = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[
            :n_results
        ]

        results = []
        for idx in ranked_indices:
            results.append(
                {
                    "text":     docs[idx],
                    "metadata": metas[idx],
                    "score":    round(rrf_scores[idx], 6),
                    "distance": round(distances[idx], 6) if idx < len(distances) else None,
                }
            )

        return results
