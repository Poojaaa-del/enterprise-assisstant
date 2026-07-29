# backend/agents/verification.py
"""
VerificationAgent
Checks whether an AI-generated answer is grounded in the retrieved source chunks.
Uses Global Multi-Chunk Answer Containment, Key Entity matching, and LLM verification 
to calculate true end-to-end groundedness confidence.
"""

import json
import os
import re
from typing import Any, Dict, List

# Try importing modern or legacy Google GenAI SDK gracefully without Pylance warnings
try:
    from google import genai as genai_new  # type: ignore
    GENAI_VERSION = "new"
except ImportError:
    try:
        import google.generativeai as genai_legacy  # type: ignore
        GENAI_VERSION = "legacy"
    except ImportError:
        GENAI_VERSION = None


class VerificationAgent:
    """
    Evaluates whether a generated answer is supported by retrieved context.
    Uses Gemini LLM verification when available, falling back to a Global Multi-Chunk
    Containment and Key-Entity matching algorithm.
    """

    CONFIDENCE_THRESHOLD = 50  # Minimum % confidence required to accept an answer

    # Common stop words to ignore during token overlap scoring
    STOP_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "in", "on", "at", "by", "for", "with", "about", "against", "between",
        "into", "through", "during", "before", "after", "above", "below", "to",
        "from", "up", "down", "out", "of", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why", "how",
        "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
        "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s",
        "t", "can", "will", "just", "don", "should", "now", "and", "or", "what", "which",
        "did", "does", "do", "this", "that", "these", "those", "result", "associated",
        "based", "provided", "details", "following", "following:", "summary", "incident"
    }

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None

        if self.api_key and GENAI_VERSION == "new":
            try:
                self.client = genai_new.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[WARNING] [Verification] New SDK Init warning: {e}")
        elif self.api_key and GENAI_VERSION == "legacy":
            try:
                genai_legacy.configure(api_key=self.api_key)
                self.client = genai_legacy.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"[WARNING] [Verification] Legacy SDK Init warning: {e}")

    def verify(self, answer: str, chunks: List[dict]) -> dict:
        """
        Args:
            answer : The AI-generated answer string.
            chunks : List of retrieved chunk dicts (each has 'text' and 'metadata').

        Returns:
            {
                "confidence_score": int (0-100),
                "is_grounded":      bool,
                "citations":        [{ "filename", "page", "snippet", "score" }],
                "verified_answer":  str
            }
        """
        if not chunks or not answer.strip():
            return self._ungrounded_response("No source documents were retrieved or answer was empty.")

        # 1. Token & Key Entity Extraction from Generated Answer
        answer_tokens = [
            w for w in re.findall(r'\b\w+\b', answer.lower())
            if w not in self.STOP_WORDS and len(w) > 1
        ]
        
        # Extract technical entities (IP addresses, error codes, hostnames, dates)
        key_entities = set(re.findall(r'\b[A-Z0-9_\-\.]{3,}\b', answer))

        full_context_text = ""
        citation_list = []

        # 2. Compute Individual Citation Scores for UI Display
        for chunk in chunks:
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {}) if isinstance(chunk.get("metadata"), dict) else {}

            filename = meta.get("filename") or chunk.get("filename") or "Unknown"
            page = meta.get("page") or meta.get("row_index") or chunk.get("page") or "—"

            full_context_text += f"\n--- [{filename}] ---\n{text}\n"
            chunk_lower = text.lower()

            # Local chunk containment
            if answer_tokens:
                chunk_matched_tokens = [t for t in answer_tokens if t in chunk_lower]
                token_containment = len(chunk_matched_tokens) / len(answer_tokens)
            else:
                token_containment = 0.5

            if key_entities:
                chunk_matched_entities = [e for e in key_entities if e in text]
                entity_score = len(chunk_matched_entities) / len(key_entities)
                chunk_score = (entity_score * 0.7) + (token_containment * 0.3)
            else:
                chunk_score = token_containment

            snippet = text[:250].strip().replace("\n", " ")
            if len(text) > 250:
                snippet += "…"

            citation_list.append({
                "filename": filename,
                "page": str(page),
                "snippet": snippet,
                "score": round(chunk_score * 100, 1)
            })

        # Sort citations by relevance score descending
        citation_list.sort(key=lambda c: c["score"], reverse=True)
        top_citations = citation_list[:3]

        # 3. Global Multi-Chunk Containment Calculation
        # Evaluates answer facts against ALL retrieved chunks combined
        full_context_lower = full_context_text.lower()
        
        if answer_tokens:
            global_matched_tokens = [t for t in answer_tokens if t in full_context_lower]
            global_token_score = len(global_matched_tokens) / len(answer_tokens)
        else:
            global_token_score = 0.5

        if key_entities:
            global_matched_entities = [e for e in key_entities if e in full_context_text]
            global_entity_score = len(global_matched_entities) / len(key_entities)
            global_combined_score = (global_entity_score * 0.7) + (global_token_score * 0.3)
        else:
            global_combined_score = global_token_score

        fallback_confidence = int(round(global_combined_score * 100))

        # 4. Groundedness Verification (LLM Check with Algorithmic Fallback)
        llm_result = self._verify_with_llm(answer, full_context_text)

        if llm_result is not None:
            confidence_score = llm_result["confidence"]
            is_grounded = llm_result["is_grounded"]
        else:
            confidence_score = min(100, fallback_confidence)
            is_grounded = confidence_score >= self.CONFIDENCE_THRESHOLD

        verified_answer = (
            answer
            if is_grounded
            else (
                "[WARNING] I cannot verify this answer based on your uploaded enterprise documents. "
                "The retrieved context does not sufficiently ground the response. "
                "Please upload more relevant documents or rephrase your question."
            )
        )

        return {
            "confidence_score": confidence_score,
            "is_grounded": is_grounded,
            "citations": top_citations,
            "verified_answer": verified_answer,
        }

    def _verify_with_llm(self, answer: str, context: str) -> Dict[str, Any]:
        """Uses Gemini to evaluate groundedness strictly against context."""
        if not self.client:
            return None

        prompt = f"""You are an Enterprise AI Verification Auditor.
Determine whether the PROPOSED ANSWER is factually backed by the PROVIDED CONTEXT.

PROVIDED CONTEXT:
{context[:4000]}

PROPOSED ANSWER:
{answer}

Respond STRICTLY in valid JSON with these exact keys:
{{
  "confidence": <integer 0-100>,
  "is_grounded": <boolean true or false>
}}"""

        try:
            if GENAI_VERSION == "new":
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                text = response.text
            elif GENAI_VERSION == "legacy":
                response = self.client.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                text = response.text
            else:
                return None

            data = json.loads(text)
            return {
                "confidence": int(data.get("confidence", 85)),
                "is_grounded": bool(data.get("is_grounded", True))
            }
        except Exception as err:
            print(f"[WARNING] [VerificationAgent] Gemini verification fallback: {err}")
            return None

    def _ungrounded_response(self, reason: str) -> dict:
        return {
            "confidence_score": 0,
            "is_grounded": False,
            "citations": [],
            "verified_answer": (
                f"[WARNING] {reason} Please upload relevant enterprise documents before querying."
            ),
        }