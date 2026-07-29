import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def find_my_project_keys():
    email = os.environ.get("JIRA_USER_EMAIL", "").strip()
    token = os.environ.get("JIRA_API_TOKEN", "").strip()
    domain = "https://poojapvt09.atlassian.net"
    
    credential_string = f"{email}:{token}"
    encoded_credentials = base64.b64encode(credential_string.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Accept": "application/json"
    }

    # Endpoint to list all accessible projects
    url = f"{domain}/rest/api/3/project"
    
    print("📡 Fetching your exact project keys from Jira...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        projects = response.json()
        if not projects:
            print("ℹ️ Your Jira instance has no projects. You need to create one in your browser first!")
            return
            
        print("\n📋 Found the following projects on your board:")
        print("---------------------------------------------")
        for p in projects:
            print(f"🔹 Project Name: {p.get('name')}")
            print(f"   👉 EXACT KEY TO USE: '{p.get('key')}'")
            print("---------------------------------------------")
    else:
        print(f"❌ Failed to fetch projects ({response.status_code}): {response.text}")

if __name__ == "__main__":
    find_my_project_keys()