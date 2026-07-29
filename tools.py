import os
import base64
import requests
from crewai.tools import tool
    

@tool("Create Jira Ticket")
def create_jira_ticket(project_key: str, summary: str, description: str, priority: str = "Medium") -> str:
    """
    Creates a new issue/ticket in Jira Cloud using the corporate API.
    Arguments:
        project_key: The uppercase short code for the project (e.g., 'SD', 'HR', 'DEV').
        summary: The clear title/summary of the ticket.
        description: The detailed body text explaining the request.
        priority: Ticket priority level (e.g., 'Highest', 'High', 'Medium', 'Low').
    Returns:
        A string indicating successful creation with the key, or an error message.
    """
    email = os.environ.get("JIRA_USER_EMAIL", "").strip()
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    domain = "https://poojapvt09.atlassian.net"
    
    if not email or not token:
        return "Error: JIRA_USER_EMAIL or JIRA_API_TOKEN environment variables are missing."

    credential_string = f"{email}:{token}"
    encoded_credentials = base64.b64encode(credential_string.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    url = f"{domain}/rest/api/3/issue"
    payload = {
    "fields": {
        "project": {
            "key": project_key
        },
        "summary": summary,
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": description
                        }
                    ]
                }
            ]
        },
        "issuetype": {
            "name": "Task"
        }
    }
}

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            ticket_key = response.json().get("key")
            return f"Success! Jira ticket logged. Ticket Key: {ticket_key}"
        else:
            return f"Failed to create ticket ({response.status_code}): {response.text}"
    except Exception as e:
        return f"An exception occurred while connecting to Jira: {str(e)}"