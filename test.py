import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def test_raw_creation():
    email = os.environ.get("JIRA_USER_EMAIL", "").strip()
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    domain = "https://poojapvt09.atlassian.net"
    
    credential_string = f"{email}:{token}"
    encoded_credentials = base64.b64encode(credential_string.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Raw Jira v3 payload payload format
    payload = {
        "fields": {
            "project": {
                "key": "SCRUM"
            },
            "summary": "Direct Test Ticket via Python",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "This is a direct API bypass test."
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "name": "Task"  # 👈 Try changing this to "Story" if it fails!
            }
        }
    }

    url = f"{domain}/rest/api/3/issue"
    print("Sending direct raw payload to Jira...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_raw_creation()