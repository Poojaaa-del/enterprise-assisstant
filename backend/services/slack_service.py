# backend/services/slack_service.py
"""
Slack Webhook Integration Service
Dispatches rich formatted Slack Block Kit alert cards when MANDATORY or CRITICAL incidents occur.
"""
import os
import requests
from typing import Optional, Dict, Any


def send_slack_alert(
    summary: str,
    timestamp: str = "Just now",
    node_id: str = "CLUSTER_NODE_01",
    dashboard_url: Optional[str] = None,
    severity: str = "CRITICAL",
) -> Dict[str, Any]:
    """
    Sends a formatted Slack Block Kit card to SLACK_WEBHOOK_URL.

    Environment variables expected:
      - SLACK_WEBHOOK_URL

    Returns:
        Dict: { "status": "SUCCESS" | "FAILED" | "SKIPPED", "detail": str }
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()

    if not webhook_url or "YOUR/WEBHOOK" in webhook_url:
        print("[INFO] [SlackService] SLACK_WEBHOOK_URL unconfigured or placeholder. Skipping notification.")
        return {
            "status": "SKIPPED",
            "detail": "Slack webhook URL is unconfigured in environment.",
        }

    link_target = dashboard_url or "http://localhost:5173"

    # Slack Block Kit payload structure
    block_payload = {
        "text": f"🚨 LogTriage AI Alert: [{severity}] Incident Flagged on {node_id}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 LogTriage AI Alert — [{severity}] Anomaly Detected",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Node Identifier:*\n`{node_id}`"},
                    {"type": "mrkdwn", "text": f"*Timestamp:*\n{timestamp}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Incident Summary:*\n```{summary[:500]}```",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🖥️ Open LogTriage AI Dashboard",
                            "emoji": True,
                        },
                        "url": link_target,
                        "style": "danger",
                    }
                ],
            },
        ],
    }

    try:
        response = requests.post(webhook_url, json=block_payload, timeout=8)
        if response.status_code == 200:
            print(f"[OK] [SlackService] Slack alert dispatched successfully to webhook.")
            return {
                "status": "SUCCESS",
                "detail": "Slack notification card delivered.",
            }
        else:
            print(f"[ERROR] [SlackService] Slack API status {response.status_code}: {response.text}")
            return {
                "status": "FAILED",
                "detail": f"Slack API status {response.status_code}: {response.text[:200]}",
            }
    except Exception as exc:
        print(f"[ERROR] [SlackService] Network exception sending Slack alert: {exc}")
        return {
            "status": "FAILED",
            "detail": f"Network exception: {str(exc)}",
        }
