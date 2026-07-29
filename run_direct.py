import os
from tools import create_jira_ticket  # Assumes your tool is in tools.py

def execute_direct_ticket():
    print("🚀 Bypassing LLM framework to execute the tool directly...")
    
    # Read environment variables dynamically from system / .env instead of hardcoding secrets
    os.environ["JIRA_USER_EMAIL"] = os.getenv("JIRA_USER_EMAIL", "poojapvt09@gmail.com")
    os.environ["JIRA_API_TOKEN"] = os.getenv("JIRA_API_TOKEN", "YOUR_JIRA_API_TOKEN_HERE") 

    # Execute the function directly with your target parameters
    result = create_jira_ticket.run(
        project_key="SCRUM",  # Official project key
        summary="Update Remote Work Expense Policy Guidelines",
        description="Please log a high-priority Jira ticket to update the remote work expense policy guidelines.",
        priority="High"
    )

    print("\n🤖 Direct Execution Result:")
    print(result)

if __name__ == "__main__":
    execute_direct_ticket()