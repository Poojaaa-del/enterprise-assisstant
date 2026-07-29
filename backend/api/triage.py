# # backend/api/triage.py
# import os
# import re
# import sqlite3
# import requests
# from fastapi import APIRouter, HTTPException, Depends
# from pydantic import BaseModel
# from groq import Groq
# from dotenv import load_dotenv

# from typing import Optional
# from services.jira_service import create_jira_issue
# from services.slack_service import send_slack_alert

# # Updated security verification dependency
# from api.auth import get_current_user

# # Force reload environment variables to prevent cached settings
# load_dotenv(override=True)

# # Pulls cleanly from your working agents package layout
# from agents import PlannerAgent, RetrievalAgent

# # ---------------------------------------------------------------------------
# # Log Content Validation Guardrail
# # Pure regex — zero LLM calls, fires before any expensive pipeline work.
# # ---------------------------------------------------------------------------
# _LOG_TIMESTAMP = re.compile(
#     r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}:\d{2}|\[\d{4})"
# )
# _LOG_LEVEL = re.compile(
#     r"\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL|TRACE|NOTICE|SEVERE)\b",
#     re.IGNORECASE,
# )
# _STACK_TRACE = re.compile(
#     r"(Traceback|at\s+\w[\w.]+\([\w.:]+\)|Exception:|Error:|File \".+\",\s+line\s+\d+)",
#     re.IGNORECASE,
# )
# _KEY_VALUE_PAIR = re.compile(r"[\w.-]+=\S+")
# _HTTP_STATUS = re.compile(r"\b[45]\d{2}\b")

# _CHITCHAT_ROOTS: frozenset = frozenset({
#     "hi", "hey", "heyy", "hello", "bye", "goodbye",
#     "thanks", "thank", "howdy", "greetings", "okay", "ok",
#     "test", "testing", "yo", "sup",
# })
# _CHITCHAT_PHRASES: frozenset = frozenset({
#     "hi", "hey", "hello", "greetings", "good morning", "good afternoon",
#     "good evening", "howdy", "thanks", "thank you", "ty", "thx",
#     "who are you", "what can you do", "what do you do", "help me",
#     "what is this", "how does this work", "bye", "goodbye", "see you",
#     "cya", "ok", "okay", "cool", "awesome", "great", "nice", "got it",
#     "sure", "yes", "no", "nope", "yep", "what are you",
#     "are you an ai", "are you a bot", "test", "testing",
# })

# _NON_LOG_RESPONSE = {
#     "status": "invalid_input",
#     "classification": "LOW_PRIORITY",
#     "severity": "INFO",
#     "incident_type": "Non-Log Input Detected",
#     "message": "Conversational input detected. Please paste raw system log traces.",
#     "root_cause_analysis": (
#         "The input provided appears to be conversational text rather than log data or "
#         "diagnostic traces. Please paste a raw log snippet, stack trace, or system "
#         "event log for triage analysis."
#     ),
#     "recommended_actions": [
#         "Paste system log output or error stack traces into the input field.",
#         "Or click 'Load Sample Incidents Data' to test the analyzer with a real log payload.",
#     ],
#     "citations": [],
#     "jira_key": "NOT_CREATED",
#     "slack_status": "Skipped"
# }


# def _is_non_log_input(text: str) -> bool:
#     """
#     Returns True when *text* is clearly conversational / chit-chat or lacks any
#     structural markers that identify it as a real system log or diagnostic trace.
#     Checks are ordered cheapest-first and short-circuit on the first match.
#     """
#     stripped = text.strip()

#     # 1. Trivially short — cannot be a meaningful log entry
#     if len(stripped) < 15:
#         return True

#     # 2. Exact chit-chat phrase match (normalise punctuation)
#     normalized = re.sub(r"[^\w\s]", "", stripped.lower())
#     if normalized in _CHITCHAT_PHRASES:
#         return True

#     # 3. Short phrase (≤ 4 words) whose first/only tokens are greeting roots
#     words = normalized.split()
#     if len(words) <= 4 and any(w in _CHITCHAT_ROOTS for w in words):
#         return True

#     # 4. Require at least ONE structural log signal to pass through
#     has_log_signal = (
#         bool(_LOG_TIMESTAMP.search(stripped))
#         or bool(_LOG_LEVEL.search(stripped))
#         or bool(_STACK_TRACE.search(stripped))
#         or bool(_KEY_VALUE_PAIR.search(stripped))
#         or bool(_HTTP_STATUS.search(stripped))
#     )
#     return not has_log_signal

# from pathlib import Path

# router = APIRouter(prefix="/api/v1", tags=["Incident Triage Engine"])

# BASE_DIR = Path(__file__).resolve().parent.parent
# DATABASE_PATH = str(BASE_DIR / "triage.db")

# class EnvironmentContext(BaseModel):
#     emails: list[str]
#     local_files: list[str]

# class TriageRequest(BaseModel):
#     task_name: str
#     context: EnvironmentContext

# class IncidentEscalateRequest(BaseModel):
#     incident_id: int
#     summary: Optional[str] = None
#     description: Optional[str] = None
#     severity: Optional[str] = "HIGH"

# planner = PlannerAgent()
# retriever = RetrievalAgent()
# groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# # Protected Endpoint: Requires Valid Bearer Token
# @router.post("/triage")
# async def process_incident_stream(payload: TriageRequest, current_user=Depends(get_current_user)):
#     try:
#         combined_text = "\n".join(payload.context.local_files)

#         # --- Non-Log Input Guardrail (no LLM cost, no false escalations, NO DB insertion, NO Jira/Slack calls) ---
#         if _is_non_log_input(combined_text):
#             print(f"[INFO] [Triage Guardrail] Non-log input blocked: '{combined_text[:80]}'")
#             return _NON_LOG_RESPONSE

#         # 1. Run the Planner Agent to structure the incident raw metadata
#         planner_analysis = planner.analyze_incident(combined_text)
        
#         # 2. Extract Vector Knowledge using the structured analysis dictionary
#         context, citation = retriever().extract_compliance_context(planner_analysis)
        
#         # 3. Read the urgency metrics directly out of the Planner's structural logic
#         severity_hint = planner_analysis.get("severity_hint", "LOW").upper()
#         classification = "MANDATORY" if "CRITICAL" in severity_hint or "HIGH" in severity_hint else "LOW_PRIORITY"
#         summary_msg = planner_analysis.get("security_anomaly_summary", "Analysis complete.")
        
#         jira_key = "NOT_CREATED"
#         slack_status = "Skipped"
        
#         # 4. Trigger real enterprise integrations if a critical compliance issue was found
#         if classification == "MANDATORY":
#             jira_result = create_jira_issue(
#                 summary=payload.task_name,
#                 description=f"System anomaly detected:\n{combined_text[:1500]}",
#                 severity=severity_hint
#             )
#             jira_key = jira_result.get("key", "NOT_CREATED")
            
#             slack_res = send_slack_alert(
#                 summary=summary_msg,
#                 timestamp="Just now",
#                 node_id=planner_analysis.get("service_origin", "CLUSTER_NODE_01"),
#                 severity=severity_hint
#             )
#             slack_status = slack_res.get("status", "FAILED")
            
#         # 5. Commit structured records scoped to the current user
#         conn = sqlite3.connect(DATABASE_PATH)
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO compliance_logs (user_id, file_name, file_content, status, jira_key, slack_status) VALUES (?, ?, ?, ?, ?, ?)",
#             (current_user.id, payload.task_name, combined_text, classification, jira_key, slack_status)
#         )
#         conn.commit()
#         new_id = cursor.lastrowid
#         conn.close()
        
#         return {
#             "id": new_id,
#             "status": "SUCCESS",
#             "classification": classification,
#             "agent_executed": "GUARDCORE_ORCHESTRATOR",
#             "message": summary_msg,
#             "citation": citation,
#             "jira_key": jira_key,
#             "slack_status": slack_status,
#             "extracted_meta": planner_analysis,
#             "actions_taken": [f"Jira State ({jira_key})", f"Slack State ({slack_status})"]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # User-Scoped Read Route: Returns only the current user's logs
# @router.get("/history")
# async def get_triage_history(current_user=Depends(get_current_user)):
#     try:
#         conn = sqlite3.connect(DATABASE_PATH)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT * FROM compliance_logs WHERE user_id = ? ORDER BY id DESC",
#             (current_user.id,)
#         )
#         rows = cursor.fetchall()
#         records = [dict(r) for r in rows]
#         conn.close()
#         return records
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # Dedicated Incident Escalation Endpoint (Module 1.1 & 1.2)
# @router.post("/incidents/escalate")
# async def escalate_incident(payload: IncidentEscalateRequest, current_user=Depends(get_current_user)):
#     try:
#         conn = sqlite3.connect(DATABASE_PATH)
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT file_name, file_content, jira_key FROM compliance_logs WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
#             (payload.incident_id, current_user.id)
#         )
#         row = cursor.fetchone()
#         if not row:
#             conn.close()
#             raise HTTPException(status_code=404, detail="Incident entry not found or access denied")
            
#         file_name, file_content, current_jira = row
        
#         summary_text = payload.summary or file_name or "Manual Escalation Alert"
#         desc_text = payload.description or f"Record #{payload.incident_id} forced priority review.\n\nContent:\n{file_content[:1500] if file_content else ''}"
        
#         jira_res = create_jira_issue(
#             summary=summary_text,
#             description=desc_text,
#             severity=payload.severity or "HIGH"
#         )
#         jira_key = jira_res.get("key", "SEC-1001")
#         jira_url = jira_res.get("url", "")

#         slack_res = send_slack_alert(
#             summary=f"Escalated Incident #{payload.incident_id}: {summary_text}",
#             timestamp="Just now",
#             node_id=f"INCIDENT_#{payload.incident_id}",
#             severity=payload.severity or "HIGH"
#         )
#         slack_status = slack_res.get("status", "SUCCESS")
            
#         cursor.execute(
#             "UPDATE compliance_logs SET status = 'MANDATORY', jira_key = ?, slack_status = ? WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
#             (jira_key, slack_status, payload.incident_id, current_user.id)
#         )
#         conn.commit()
#         conn.close()
        
#         return {
#             "status": "SUCCESS",
#             "incident_id": payload.incident_id,
#             "jira_key": jira_key,
#             "jira_url": jira_url,
#             "slack_status": slack_status,
#             "detail": f"Incident #{payload.incident_id} escalated to MANDATORY status and Jira ticket {jira_key} created."
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # Backward compatible endpoint
# @router.post("/logs/{log_id}/escalate")
# async def escalate_compliance_node(log_id: int, current_user=Depends(get_current_user)):
#     return await escalate_incident(IncidentEscalateRequest(incident_id=log_id), current_user=current_user)

# # Protected Endpoint: Requires Valid Bearer Token
# @router.delete("/logs/{log_id}")
# async def purge_compliance_node(log_id: int, current_user=Depends(get_current_user)):
#     try:
#         conn = sqlite3.connect(DATABASE_PATH)
#         cursor = conn.cursor()
#         # Guard: only delete records owned by the current user
#         cursor.execute(
#             "DELETE FROM compliance_logs WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
#             (log_id, current_user.id)
#         )
#         conn.commit()
#         affected = cursor.rowcount
#         conn.close()
#         if affected == 0:
#             raise HTTPException(status_code=404, detail="Log Record not found or access denied")
#         return {"status": "SUCCESS", "detail": f"Log Record #{log_id} permanently purged."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # Bulk Cleanup / Purge Endpoint: Deletes junk entries (< 10 chars or greeting words)
# @router.post("/logs/purge-junk")
# async def purge_junk_logs(current_user=Depends(get_current_user)):
#     try:
#         conn = sqlite3.connect(DATABASE_PATH)
#         cursor = conn.cursor()
#         # Query user's records (or unowned records) to evaluate
#         cursor.execute(
#             "SELECT id, file_content, file_name FROM compliance_logs WHERE user_id = ? OR user_id IS NULL",
#             (current_user.id,)
#         )
#         rows = cursor.fetchall()
#         junk_ids = []
#         for row_id, content, name in rows:
#             text = (content or "").strip()
#             # Mark as junk if empty, shorter than 10 chars, or matches chit-chat guardrail
#             if len(text) < 10 or _is_non_log_input(text):
#                 junk_ids.append(row_id)
        
#         if junk_ids:
#             cursor.executemany(
#                 "DELETE FROM compliance_logs WHERE id = ?",
#                 [(jid,) for jid in junk_ids]
#             )
#             conn.commit()
        
#         purged_count = len(junk_ids)
#         conn.close()
#         return {
#             "status": "SUCCESS",
#             "purged_count": purged_count,
#             "detail": f"Successfully purged {purged_count} junk incident log record(s)."
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))



# backend/api/triage.py
import os
import re
import sqlite3
import requests
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

from services.jira_service import create_jira_issue
from services.slack_service import send_slack_alert

# Updated security verification dependency
from api.auth import get_current_user

# Force reload environment variables to prevent cached settings
load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Lazy-loading agent singletons to avoid OOM Status 137 during server boot
# ---------------------------------------------------------------------------
_planner_instance = None
_retriever_instance = None
_groq_client_instance = None

def get_planner():
    global _planner_instance
    if _planner_instance is None:
        from agents import PlannerAgent
        _planner_instance = PlannerAgent()
    return _planner_instance

def get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        from agents import RetrievalAgent
        _retriever_instance = RetrievalAgent()
    return _retriever_instance

def get_groq_client():
    global _groq_client_instance
    if _groq_client_instance is None:
        _groq_client_instance = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _groq_client_instance

# ---------------------------------------------------------------------------
# Log Content Validation Guardrail
# Pure regex — zero LLM calls, fires before any expensive pipeline work.
# ---------------------------------------------------------------------------
_LOG_TIMESTAMP = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}:\d{2}:\d{2}|\[\d{4})"
)
_LOG_LEVEL = re.compile(
    r"\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL|TRACE|NOTICE|SEVERE)\b",
    re.IGNORECASE,
)
_STACK_TRACE = re.compile(
    r"(Traceback|at\s+\w[\w.]+\([\w.:]+\)|Exception:|Error:|File \".+\",\s+line\s+\d+)",
    re.IGNORECASE,
)
_KEY_VALUE_PAIR = re.compile(r"[\w.-]+=\S+")
_HTTP_STATUS = re.compile(r"\b[45]\d{2}\b")

_CHITCHAT_ROOTS: frozenset = frozenset({
    "hi", "hey", "heyy", "hello", "bye", "goodbye",
    "thanks", "thank", "howdy", "greetings", "okay", "ok",
    "test", "testing", "yo", "sup",
})
_CHITCHAT_PHRASES: frozenset = frozenset({
    "hi", "hey", "hello", "greetings", "good morning", "good afternoon",
    "good evening", "howdy", "thanks", "thank you", "ty", "thx",
    "who are you", "what can you do", "what do you do", "help me",
    "what is this", "how does this work", "bye", "goodbye", "see you",
    "cya", "ok", "okay", "cool", "awesome", "great", "nice", "got it",
    "sure", "yes", "no", "nope", "yep", "what are you",
    "are you an ai", "are you a bot", "test", "testing",
})

_NON_LOG_RESPONSE = {
    "status": "invalid_input",
    "classification": "LOW_PRIORITY",
    "severity": "INFO",
    "incident_type": "Non-Log Input Detected",
    "message": "Conversational input detected. Please paste raw system log traces.",
    "root_cause_analysis": (
        "The input provided appears to be conversational text rather than log data or "
        "diagnostic traces. Please paste a raw log snippet, stack trace, or system "
        "event log for triage analysis."
    ),
    "recommended_actions": [
        "Paste system log output or error stack traces into the input field.",
        "Or click 'Load Sample Incidents Data' to test the analyzer with a real log payload.",
    ],
    "citations": [],
    "jira_key": "NOT_CREATED",
    "slack_status": "Skipped"
}


def _is_non_log_input(text: str) -> bool:
    """
    Returns True when *text* is clearly conversational / chit-chat or lacks any
    structural markers that identify it as a real system log or diagnostic trace.
    Checks are ordered cheapest-first and short-circuit on the first match.
    """
    stripped = text.strip()

    # 1. Trivially short — cannot be a meaningful log entry
    if len(stripped) < 15:
        return True

    # 2. Exact chit-chat phrase match (normalise punctuation)
    normalized = re.sub(r"[^\w\s]", "", stripped.lower())
    if normalized in _CHITCHAT_PHRASES:
        return True

    # 3. Short phrase (≤ 4 words) whose first/only tokens are greeting roots
    words = normalized.split()
    if len(words) <= 4 and any(w in _CHITCHAT_ROOTS for w in words):
        return True

    # 4. Require at least ONE structural log signal to pass through
    has_log_signal = (
        bool(_LOG_TIMESTAMP.search(stripped))
        or bool(_LOG_LEVEL.search(stripped))
        or bool(_STACK_TRACE.search(stripped))
        or bool(_KEY_VALUE_PAIR.search(stripped))
        or bool(_HTTP_STATUS.search(stripped))
    )
    return not has_log_signal


router = APIRouter(prefix="/api/v1", tags=["Incident Triage Engine"])

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = str(BASE_DIR / "triage.db")

class EnvironmentContext(BaseModel):
    emails: list[str]
    local_files: list[str]

class TriageRequest(BaseModel):
    task_name: str
    context: EnvironmentContext

class IncidentEscalateRequest(BaseModel):
    incident_id: int
    summary: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = "HIGH"


# Protected Endpoint: Requires Valid Bearer Token
@router.post("/triage")
async def process_incident_stream(payload: TriageRequest, current_user=Depends(get_current_user)):
    try:
        combined_text = "\n".join(payload.context.local_files)

        # --- Non-Log Input Guardrail (no LLM cost, no false escalations, NO DB insertion, NO Jira/Slack calls) ---
        if _is_non_log_input(combined_text):
            print(f"[INFO] [Triage Guardrail] Non-log input blocked: '{combined_text[:80]}'")
            return _NON_LOG_RESPONSE

        # 1. Run the Planner Agent (Lazy Loaded)
        planner = get_planner()
        planner_analysis = planner.analyze_incident(combined_text)
        
        # 2. Extract Vector Knowledge using the structured analysis dictionary (Lazy Loaded)
        retriever = get_retriever()
        context, citation = retriever.extract_compliance_context(planner_analysis)
        
        # 3. Read the urgency metrics directly out of the Planner's structural logic
        severity_hint = planner_analysis.get("severity_hint", "LOW").upper()
        classification = "MANDATORY" if "CRITICAL" in severity_hint or "HIGH" in severity_hint else "LOW_PRIORITY"
        summary_msg = planner_analysis.get("security_anomaly_summary", "Analysis complete.")
        
        jira_key = "NOT_CREATED"
        slack_status = "Skipped"
        
        # 4. Trigger real enterprise integrations if a critical compliance issue was found
        if classification == "MANDATORY":
            jira_result = create_jira_issue(
                summary=payload.task_name,
                description=f"System anomaly detected:\n{combined_text[:1500]}",
                severity=severity_hint
            )
            jira_key = jira_result.get("key", "NOT_CREATED")
            
            slack_res = send_slack_alert(
                summary=summary_msg,
                timestamp="Just now",
                node_id=planner_analysis.get("service_origin", "CLUSTER_NODE_01"),
                severity=severity_hint
            )
            slack_status = slack_res.get("status", "FAILED")
            
        # 5. Commit structured records scoped to the current user
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO compliance_logs (user_id, file_name, file_content, status, jira_key, slack_status) VALUES (?, ?, ?, ?, ?, ?)",
            (current_user.id, payload.task_name, combined_text, classification, jira_key, slack_status)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return {
            "id": new_id,
            "status": "SUCCESS",
            "classification": classification,
            "agent_executed": "GUARDCORE_ORCHESTRATOR",
            "message": summary_msg,
            "citation": citation,
            "jira_key": jira_key,
            "slack_status": slack_status,
            "extracted_meta": planner_analysis,
            "actions_taken": [f"Jira State ({jira_key})", f"Slack State ({slack_status})"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User-Scoped Read Route: Returns only the current user's logs
@router.get("/history")
async def get_triage_history(current_user=Depends(get_current_user)):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM compliance_logs WHERE user_id = ? ORDER BY id DESC",
            (current_user.id,)
        )
        rows = cursor.fetchall()
        records = [dict(r) for r in rows]
        conn.close()
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Dedicated Incident Escalation Endpoint
@router.post("/incidents/escalate")
async def escalate_incident(payload: IncidentEscalateRequest, current_user=Depends(get_current_user)):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_name, file_content, jira_key FROM compliance_logs WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
            (payload.incident_id, current_user.id)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Incident entry not found or access denied")
            
        file_name, file_content, current_jira = row
        
        summary_text = payload.summary or file_name or "Manual Escalation Alert"
        desc_text = payload.description or f"Record #{payload.incident_id} forced priority review.\n\nContent:\n{file_content[:1500] if file_content else ''}"
        
        jira_res = create_jira_issue(
            summary=summary_text,
            description=desc_text,
            severity=payload.severity or "HIGH"
        )
        jira_key = jira_res.get("key", "SEC-1001")
        jira_url = jira_res.get("url", "")

        slack_res = send_slack_alert(
            summary=f"Escalated Incident #{payload.incident_id}: {summary_text}",
            timestamp="Just now",
            node_id=f"INCIDENT_#{payload.incident_id}",
            severity=payload.severity or "HIGH"
        )
        slack_status = slack_res.get("status", "SUCCESS")
            
        cursor.execute(
            "UPDATE compliance_logs SET status = 'MANDATORY', jira_key = ?, slack_status = ? WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
            (jira_key, slack_status, payload.incident_id, current_user.id)
        )
        conn.commit()
        conn.close()
        
        return {
            "status": "SUCCESS",
            "incident_id": payload.incident_id,
            "jira_key": jira_key,
            "jira_url": jira_url,
            "slack_status": slack_status,
            "detail": f"Incident #{payload.incident_id} escalated to MANDATORY status and Jira ticket {jira_key} created."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Backward compatible endpoint
@router.post("/logs/{log_id}/escalate")
async def escalate_compliance_node(log_id: int, current_user=Depends(get_current_user)):
    return await escalate_incident(IncidentEscalateRequest(incident_id=log_id), current_user=current_user)

# Protected Endpoint: Requires Valid Bearer Token
@router.delete("/logs/{log_id}")
async def purge_compliance_node(log_id: int, current_user=Depends(get_current_user)):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM compliance_logs WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
            (log_id, current_user.id)
        )
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        if affected == 0:
            raise HTTPException(status_code=404, detail="Log Record not found or access denied")
        return {"status": "SUCCESS", "detail": f"Log Record #{log_id} permanently purged."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bulk Cleanup / Purge Endpoint
@router.post("/logs/purge-junk")
async def purge_junk_logs(current_user=Depends(get_current_user)):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, file_content, file_name FROM compliance_logs WHERE user_id = ? OR user_id IS NULL",
            (current_user.id,)
        )
        rows = cursor.fetchall()
        junk_ids = []
        for row_id, content, name in rows:
            text = (content or "").strip()
            if len(text) < 10 or _is_non_log_input(text):
                junk_ids.append(row_id)
        
        if junk_ids:
            cursor.executemany(
                "DELETE FROM compliance_logs WHERE id = ?",
                [(jid,) for jid in junk_ids]
            )
            conn.commit()
        
        purged_count = len(junk_ids)
        conn.close()
        return {
            "status": "SUCCESS",
            "purged_count": purged_count,
            "detail": f"Successfully purged {purged_count} junk incident log record(s)."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))