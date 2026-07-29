# backend/services/jira_service.py
"""
Atlassian Jira REST API Integration Service
Calls POST /rest/api/3/issue to create production Jira tickets for incident escalations.
"""
import os
import requests
from typing import Dict, Any, Optional


def create_jira_issue(
    summary: str,
    description: str,
    severity: str = "HIGH",
    project_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an issue in Atlassian Jira Cloud via REST API v3.

    Environment variables expected:
      - JIRA_URL / JIRA_DOMAIN (e.g., 'yourcompany.atlassian.net' or 'https://yourcompany.atlassian.net')
      - JIRA_EMAIL
      - JIRA_API_TOKEN
      - JIRA_PROJECT_KEY (default: 'SCRUM' or 'SEC')

    Returns:
        Dict: { "key": str, "url": str, "status": "SUCCESS" | "FAILED" | "MOCK" }
    """
    jira_domain = os.getenv("JIRA_DOMAIN") or os.getenv("JIRA_URL", "")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")
    target_project = project_key or os.getenv("JIRA_PROJECT_KEY", "SCRUM")

    # Clean domain string
    domain_clean = jira_domain.replace("https://", "").replace("http://", "").strip("/")

    # Fallback simulation if Jira credentials are unconfigured or placeholder values
    if not jira_token or not jira_email or not domain_clean or "YOUR_" in jira_token or "YOUR_" in jira_email:
        print(f"[INFO] [JiraService] Jira credentials unconfigured/placeholder. Generating mock key.")
        mock_key = f"{target_project}-{(hash(summary + description) % 8999) + 1000}"
        return {
            "key": mock_key,
            "url": f"https://mock-jira.atlassian.net/browse/{mock_key}",
            "status": "MOCK",
            "detail": "Jira API credentials unconfigured in environment; mock ticket generated.",
        }

    api_endpoint = f"https://{domain_clean}/rest/api/3/issue"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Atlassian Jira Document Format (ADF) for v3 API
    issue_payload = {
        "fields": {
            "project": {"key": target_project},
            "summary": f"[LogTriage AI] [{severity}] {summary[:120]}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Incident Escalation Summary:\n{description[:2000]}",
                            }
                        ],
                    }
                ],
            },
            "issuetype": {"name": "Task"},
        }
    }

    try:
        response = requests.post(
            api_endpoint,
            json=issue_payload,
            headers=headers,
            auth=(jira_email, jira_token),
            timeout=10,
        )

        if response.status_code == 201:
            data = response.json()
            issue_key = data.get("key", f"{target_project}-1001")
            issue_url = f"https://{domain_clean}/browse/{issue_key}"
            print(f"[OK] [JiraService] Jira ticket created successfully: {issue_key}")
            return {
                "key": issue_key,
                "url": issue_url,
                "status": "SUCCESS",
                "detail": "Jira issue created successfully via REST API v3.",
            }
        else:
            print(f"[ERROR] [JiraService] Jira API returned status {response.status_code}: {response.text}")
            fallback_key = f"{target_project}-ERR"
            return {
                "key": fallback_key,
                "url": f"https://{domain_clean}/browse/{fallback_key}",
                "status": "FAILED",
                "detail": f"Jira API status {response.status_code}: {response.text[:200]}",
            }
    except Exception as exc:
        print(f"[ERROR] [JiraService] Exception connecting to Jira API: {exc}")
        fallback_key = f"{target_project}-ERR"
        return {
            "key": fallback_key,
            "url": f"https://{domain_clean}/browse/{fallback_key}",
            "status": "FAILED",
            "detail": f"Network exception: {str(exc)}",
        }
