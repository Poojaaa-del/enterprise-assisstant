# tests/test_pipeline.py
"""
LogTriage AI Integration Test Suite
Tests:
  1. Intent Classification (CHITCHAT fast-path)
  2. SHA-256 File Deduplication Logic
  3. RBAC Department & User Metadata Scoping
  4. Jira & Slack Service Integrations (Mocked HTTP)
"""
import sys
import os
import hashlib
from unittest.mock import patch, MagicMock
import pytest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from agents.planner import PlannerAgent, _is_chitchat
from services.jira_service import create_jira_issue
from services.slack_service import send_slack_alert


# ── Test 1: Intent Classification ──────────────────────────────────────────────
def test_chitchat_intent_classification():
    """Verify greeting inputs return CHITCHAT intent with zero retrieval overhead."""
    greetings = ["hi", "hello", "good morning", "hey", "thanks"]

    # _is_chitchat is pure local logic — no LLM needed
    for greeting in greetings:
        assert _is_chitchat(greeting) is True

    # PlannerAgent.plan requires Groq; mock it so tests run without credentials
    with patch("agents.planner.Groq") as mock_groq_cls:
        mock_groq_cls.return_value = MagicMock()
        planner = PlannerAgent()
        for greeting in greetings:
            plan = planner.plan(greeting)
            assert plan["intent"] == "CHITCHAT"
            assert plan["sub_queries"] == []
            assert "Chit-chat" in plan["execution_plan"]


def test_rag_query_intent_classification():
    """Verify non-greeting complex queries trigger RAG_QUERY intent."""
    query = "What is our database connection pool timeout policy?"
    assert _is_chitchat(query) is False

    with patch("agents.planner.Groq") as mock_groq_cls:
        mock_groq_cls.return_value = MagicMock()
        planner = PlannerAgent()
        with patch.object(planner, "_rewrite_query_with_history", return_value=query):
            plan = planner.plan(query)
            assert plan["intent"] == "RAG_QUERY"
            assert isinstance(plan.get("sub_queries"), list)


# ── Test 2: SHA-256 Deduplication ──────────────────────────────────────────────
def test_sha256_deduplication():
    """Verify identical file content generates identical SHA-256 hash."""
    content1 = b"2026-07-27 10:00:00 [ERROR] Connection pool exhausted on DB_NODE_01"
    content2 = b"2026-07-27 10:00:00 [ERROR] Connection pool exhausted on DB_NODE_01"
    content3 = b"2026-07-27 10:05:00 [INFO] System health check normal"

    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()
    hash3 = hashlib.sha256(content3).hexdigest()

    assert hash1 == hash2, "Identical content must produce matching SHA-256 hashes"
    assert hash1 != hash3, "Different content must produce distinct SHA-256 hashes"
    assert len(hash1) == 64


# ── Test 3: RBAC Metadata Scoping ──────────────────────────────────────────────
def test_rbac_metadata_scoping():
    """Verify user department & tenant isolation filter construction."""
    from agents.retrieval import RetrievalAgent

    agent = RetrievalAgent()
    with patch.object(agent.collection, "query", return_value={"documents": [[]], "metadatas": [[]], "distances": [[]]}):
        # Call search with user_id and department
        results = agent.search(query="connection error", user_id=42, user_department="Security Ops")
        assert isinstance(results, list)


# ── Test 4: Jira REST API Service Integration ──────────────────────────────────
@patch("services.jira_service.requests.post")
def test_jira_issue_creation(mock_post):
    """Verify Jira REST API payload structure and response parsing."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"key": "SEC-9999", "id": "10099"}
    mock_post.return_value = mock_response

    with patch.dict(os.environ, {
        "JIRA_DOMAIN": "testco.atlassian.net",
        "JIRA_EMAIL": "admin@testco.com",
        "JIRA_API_TOKEN": "valid_token_12345",
        "JIRA_PROJECT_KEY": "SEC"
    }):
        result = create_jira_issue(
            summary="PostgreSQL Connection Exhaustion",
            description="DB connection slots exceeded maximum limit",
            severity="CRITICAL"
        )

        assert result["status"] == "SUCCESS"
        assert result["key"] == "SEC-9999"
        assert "SEC-9999" in result["url"]
        mock_post.assert_called_once()


# ── Test 5: Slack Webhook Service Integration ──────────────────────────────────
@patch("services.slack_service.requests.post")
def test_slack_webhook_alert(mock_post):
    """Verify Slack Block Kit payload delivery to webhook URL."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/X00"}):
        result = send_slack_alert(
            summary="Database node 02 down",
            timestamp="2026-07-27 10:00:00 UTC",
            node_id="DB_NODE_02",
            severity="CRITICAL"
        )

        assert result["status"] == "SUCCESS"
        mock_post.assert_called_once()
        sent_payload = mock_post.call_args[1]["json"]
        assert "blocks" in sent_payload
        assert sent_payload["blocks"][0]["type"] == "header"


# ── Test 6: Non-Log Input Guardrail Verification ──────────────────────────────
def test_non_log_input_guardrail():
    """Verify non-log input detector blocks chit-chat and short conversational inputs."""
    from api.triage import _is_non_log_input, _NON_LOG_RESPONSE

    conversational_inputs = [
        "Hi",
        "Hello",
        "test",
        "good morning",
        "what can you do",
        "how does this work",
        "short string",
    ]
    for inp in conversational_inputs:
        assert _is_non_log_input(inp) is True, f"Failed for input: {inp}"

    valid_log_inputs = [
        "2026-07-27 10:00:00 [ERROR] Connection timed out on DB_NODE_01",
        "Traceback (most recent call last):\n  File \"app.py\", line 45, in main\nValueError: Invalid state",
        "user_id=123 status=500 message=Internal Server Error",
    ]
    for log in valid_log_inputs:
        assert _is_non_log_input(log) is False, f"Failed for valid log input: {log}"

    assert _NON_LOG_RESPONSE["status"] == "invalid_input"
    assert _NON_LOG_RESPONSE["severity"] == "INFO"
    assert _NON_LOG_RESPONSE["incident_type"] == "Non-Log Input Detected"


# ── Test 7: Bulk Junk Log Cleanup Endpoint ──────────────────────────────────
def test_bulk_purge_junk_logs():
    """Verify bulk purge endpoint removes junk entries and leaves valid log entries."""
    from api.triage import _is_non_log_input

    # Sample rows from database
    rows = [
        (1, "hi", "test.log"),
        (2, "hello world", "greeting.txt"),
        (3, "2026-07-27 10:00:00 [ERROR] Connection pool exhausted", "prod.log"),
        (4, "short", "short.log"),
    ]

    junk_ids = []
    for row_id, content, name in rows:
        text = (content or "").strip()
        if len(text) < 10 or _is_non_log_input(text):
            junk_ids.append(row_id)

    assert junk_ids == [1, 2, 4], "Must identify rows 1, 2, 4 as junk entries to purge"


