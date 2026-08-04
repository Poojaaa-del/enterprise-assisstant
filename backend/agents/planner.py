# backend/agents/planner.py
import json
import os
import re
from typing import List, Optional, Any
from groq import Groq

# ---------------------------------------------------------------------------
# Chit-chat intent detection — pure local check, zero LLM calls
# ---------------------------------------------------------------------------
GREETING_PATTERNS: frozenset = frozenset({
    "hi", "heyy", "hey", "hello", "greetings",
    "good morning", "good afternoon", "good evening",
    "howdy", "thanks", "thank you", "ty", "thx",
    "who are you", "what can you do", "what do you do",
    "help", "help me", "what is this", "how does this work",
    "bye", "goodbye", "see you", "cya", "ok", "okay",
    "cool", "awesome", "great", "nice", "got it",
    "sure", "yes", "no", "nope", "yep",
    "what are you", "are you an ai", "are you a bot",
})

_CHITCHAT_RESPONSE = (
    "Hello! I am your GuardCore Enterprise Assistant. "
    "How can I help you analyze your enterprise documents, "
    "telemetry logs, or incident reports today?"
)


def _is_chitchat(query: str) -> bool:
    """Return True if query is a greeting / pleasantry / meta-question."""
    cleaned = re.sub(r"[^\w\s]", "", query.strip().lower())
    # Exact phrase match
    if cleaned in GREETING_PATTERNS:
        return True
    # Very short queries (<= 3 words) that contain a greeting root
    words = cleaned.split()
    if len(words) <= 3:
        greeting_roots = {
            "hi", "hey", "hello", "bye", "thanks", "thank",
            "howdy", "greetings", "okay", "ok",
        }
        if any(w in greeting_roots for w in words):
            return True
    return False


MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}


def extract_date_filter(query: str) -> Optional[dict]:
    """
    Extracts date expressions like '2026-07-18', 'July 18', 'Jul 18 2026' from user query.
    Returns dict: {'date': 'YYYY-MM-DD'} or None.
    """
    if not query:
        return None

    # Pattern 1: ISO date YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", query)
    if match:
        return {"date": match.group(0)}

    # Pattern 2: Month Day Year e.g. July 18 2026 or Jul 18
    match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?\b",
        query,
        re.IGNORECASE,
    )
    if match:
        m_name, day, year = match.group(1).lower(), int(match.group(2)), match.group(3)
        month_str = MONTH_MAP.get(m_name, "07")
        day_str = f"{day:02d}"
        year_str = year if year else "2026"
        return {"date": f"{year_str}-{month_str}-{day_str}"}

    return None

# Try importing Google GenAI SDK for Gemini contextual rewriting
try:
    from google import genai as genai_new  # type: ignore
    GENAI_VERSION = "new"
except ImportError:
    try:
        import google.generativeai as genai_legacy  # type: ignore
        GENAI_VERSION = "legacy"
    except ImportError:
        GENAI_VERSION = None


class PlannerAgent:
    def __init__(self):
        # Hooks directly into the existing cloud inference client matrix
        self.client = Groq()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = None

        if self.api_key and GENAI_VERSION == "new":
            try:
                self.gemini_client = genai_new.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[WARNING] [PlannerAgent] Gemini SDK Init warning: {e}")
        elif self.api_key and GENAI_VERSION == "legacy":
            try:
                genai_legacy.configure(api_key=self.api_key)
                self.gemini_client = genai_legacy.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"[WARNING] [PlannerAgent] Legacy Gemini SDK Init warning: {e}")

    def _rewrite_query_with_history(self, user_query: str, chat_history: Optional[List[Any]] = None) -> str:
        """
        Uses Gemini (with Groq fallback) to resolve pronouns and references in user_query
        (e.g., 'it', 'that node', 'the previous IP') against the last 4 chat turns.
        """
        if not chat_history:
            return user_query

        # Extract last 4 turns
        recent_history = chat_history[-4:]
        history_lines = []
        for msg in recent_history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content") or msg.get("text") or ""
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                role = getattr(msg, "role")
                content = getattr(msg, "content")
            else:
                continue
            if content:
                history_lines.append(f"{role.upper()}: {content}")

        if not history_lines:
            return user_query

        history_context = "\n".join(history_lines)
        system_instruction = (
            "You are a contextual query rewriter for an enterprise intelligence search engine.\n"
            "Given recent conversation history and a follow-up user query, rewrite the user query into a standalone search query that explicitly resolves any pronouns, ambiguous references ('it', 'that node', 'the previous IP', 'that incident', 'the server', etc.) to their specific entities.\n"
            "If the user query is already standalone and needs no context resolution, return it unchanged.\n"
            "CRITICAL: Output ONLY the rewritten search query text. Do not include quotes, markdown code fences, explanations, or preambles."
        )
        user_prompt = (
            f"--- CONVERSATION HISTORY ---\n{history_context}\n\n"
            f"--- CURRENT FOLLOW-UP QUERY ---\n{user_query}\n\n"
            f"REWRITTEN STANDALONE QUERY:"
        )

        # 1. Try Gemini first
        if self.gemini_client:
            try:
                if GENAI_VERSION == "new":
                    response = self.gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"{system_instruction}\n\n{user_prompt}"
                    )
                    rewritten = response.text.strip()
                    if rewritten:
                        print(f"[INFO] [PlannerAgent] Contextual Rewrite (Gemini): '{user_query}' -> '{rewritten}'")
                        return rewritten
                elif GENAI_VERSION == "legacy":
                    response = self.gemini_client.generate_content(f"{system_instruction}\n\n{user_prompt}")
                    rewritten = response.text.strip()
                    if rewritten:
                        print(f"[INFO] [PlannerAgent] Contextual Rewrite (Gemini Legacy): '{user_query}' -> '{rewritten}'")
                        return rewritten
            except Exception as e:
                print(f"[WARNING] [PlannerAgent] Gemini rewrite failed, falling back to Groq: {e}")

        # 2. Fallback to Groq
        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0
            )
            rewritten = completion.choices[0].message.content.strip()
            print(f"[INFO] [PlannerAgent] Contextual Rewrite (Groq): '{user_query}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            print(f"[ERROR] [PlannerAgent] Contextual rewrite fallback failed: {e}")
            return user_query

    def analyze_incident(self, raw_content: str) -> dict:
        """
        Ingests unstructured text signatures or system anomaly logs, isolating
        variables and calculating primary cross-cutting compliance concerns.
        """
        system_instruction = (
            "You are the GuardCore Sifter Agent. Your exact operational mandate is to break down "
            "raw system logs, infrastructure errors, or unstructured incident updates into clean data schemas.\n"
            "Extract or deduce these five fields: 'timestamp', 'service_origin', 'severity_hint', "
            "'isolated_error_message', and 'security_anomaly_summary'.\n\n"
            "IMPORTANT — Non-Log Input & General Query Handling:\n"
            "If the input log context contains no system logs, errors, or diagnostic telemetry (e.g. conversational chit-chat or general queries), "
            "you MUST:\n"
            "  - Set severity_hint to 'INFO'\n"
            "  - Set incident_type to 'General Query'\n"
            "  - Set isolated_error_message to 'No log content detected.'\n"
            "  - Set security_anomaly_summary to a neutral description stating no incident was found.\n"
            "  - Disable automatic mandatory escalation (do NOT set severity_hint to HIGH or CRITICAL).\n\n"
            "CRITICAL: Output your response as a single-line, valid minified JSON object ONLY. "
            "Do not wrap it in markdown code blocks like ```json. Do not include trailing prose or greetings."
        )

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": raw_content}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.0  # Force exact deterministic token outputs
            )
            
            raw_response = completion.choices[0].message.content.strip()
            
            # Defensive validation to strip out accidental markdown tags if returned
            if raw_response.startswith("```"):
                lines = raw_response.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:-1]
                raw_response = "".join(lines).replace("json", "", 1).strip()
                
            return json.loads(raw_response)
            
        except Exception as e:
            print(f"[ERROR] [Agent Matrix Failure - Planner]: {str(e)}")
            # Graceful degradation schema safety net
            # NOTE: severity_hint is 'UNKNOWN' (not CRITICAL) to prevent false auto-escalation
            return {
                "timestamp": "CURRENT_STREAM",
                "service_origin": "UNKNOWN_NODE",
                "severity_hint": "UNKNOWN",
                "isolated_error_message": raw_content[:200],
                "security_anomaly_summary": f"Automated processing bypass due to execution exception: {str(e)}"
            }

    def decompose_query(self, user_query: str, chat_history: Optional[List[Any]] = None) -> dict:
        """
        Decomposes a complex user question into an execution plan with
        sub-queries that can be run independently against the Retrieval Agent.
        Uses conversation history to resolve pronouns and references prior to decomposition.

        Returns:
            {
                "original_query": str,
                "resolved_query": str,
                "sub_queries":    [str, ...],
                "search_intent":  str,
                "execution_plan": str
            }
        """
        resolved_query = self._rewrite_query_with_history(user_query, chat_history)

        system_prompt = (
            "You are the GuardCore Planner Agent specializing in enterprise document intelligence. "
            "Given a user question, your job is to:\n"
            "1. Break it into 2-4 focused sub-queries that each target a specific piece of information.\n"
            "2. State the overall search intent in one sentence.\n"
            "3. Write a short human-readable execution plan.\n\n"
            "CRITICAL: Output ONLY a single-line minified JSON with these exact keys: "
            "'original_query', 'sub_queries' (array of strings), 'search_intent', 'execution_plan'. "
            "Do NOT wrap output in markdown code fences."
        )

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": resolved_query},
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
            )
            raw = completion.choices[0].message.content.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw   = "\n".join(lines[1:-1]).strip()
            res = json.loads(raw)
            # Enforce single sub-query to avoid multi-query embedding / search memory spikes
            subs = res.get("sub_queries") if isinstance(res, dict) else None
            if not isinstance(subs, list) or len(subs) == 0:
                # Fallback to using the fully resolved single query
                res["sub_queries"] = [resolved_query]
            else:
                # Keep only the first sub-query to prevent parallel expansion
                res["sub_queries"] = [subs[0]] if len(subs) >= 1 else [resolved_query]
            res["resolved_query"] = resolved_query
            return res

        except Exception as e:
            print(f"[ERROR] [PlannerAgent.decompose_query]: {e}")
            res = {
                "original_query": user_query,
                "resolved_query": resolved_query,
                "sub_queries":    [resolved_query],
                "search_intent":  "Answer user's enterprise document question.",
                "execution_plan": "Single-pass retrieval due to planning fallback.",
                "intent": "RAG_QUERY",
            }

        # Temporal / Date Metadata Filtering (Module 2.2)
        date_meta = extract_date_filter(user_query) or extract_date_filter(resolved_query)
        if date_meta:
            res["metadata_filter"] = date_meta
            print(f"[INFO] [PlannerAgent] Extracted temporal date filter: {date_meta}")

        return res

    # ------------------------------------------------------------------
    # Public high-level entry point used by /agent-query
    # ------------------------------------------------------------------
    def plan(self, user_query: str, chat_history: Optional[List[Any]] = None) -> dict:
        """
        Classifies intent then either:
          - Returns a CHITCHAT plan immediately (no LLM call, no retrieval needed)
          - Returns a RAG_QUERY plan via decompose_query (contextual rewrite + sub-queries)
        """
        if _is_chitchat(user_query):
            print(f"[INFO] [PlannerAgent] CHITCHAT detected: '{user_query}'")
            return {
                "intent":        "CHITCHAT",
                "resolved_query": user_query,
                "sub_queries":   [],
                "plan_summary":  "Recognized general conversational input. Responding directly without document retrieval.",
                "execution_plan": "Chit-chat bypass — no retrieval required.",
            }

        result = self.decompose_query(user_query, chat_history=chat_history)
        result["intent"] = "RAG_QUERY"
        return result
