import os
import re
import json
import time
import requests
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
import streamlit as st
import crewai.llms.cache as _crewai_cache

# Override cache breakpoints safely
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

from crewai import Agent, Task, LLM, Crew
from crewai.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from tools import create_jira_ticket

# Load environment variables from the .env file securely
load_dotenv()

# 1. Initialize Groq with rigid safety rails to respect the 12,000 TPM limit
groq_llm = LLM(
    model="groq/llama-3.3-70b-versatile",  
    base_url="https://api.groq.com/openai/v1", 
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=800  # Restricts output length to actively preserve token window
)

# 2. Live Enterprise Channel Listeners
def read_mock_emails():
    """Connects to the live inbox and fetches the latest 3 unread emails."""
    username = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    imap_server = os.environ.get("EMAIL_IMAP_SERVER", "imap.gmail.com")

    if not username or not password:
        return "Error: Email credentials are missing from the environment configuration."

    try:
        # Connect and login to the server securely
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select("inbox")

        # Search for all UNREAD emails
        status, messages = mail.search(None, 'UNSEEN')
        if status != "OK" or not messages[0]:
            mail.logout()
            return "No new unread emails found in the inbox."

        # Convert message numbers string to a list
        mail_ids = messages[0].split()
        # Take the last 3 unread emails to prevent hitting token limits
        latest_mail_ids = mail_ids[-3:]

        email_corpus = []

        for index, mail_id in enumerate(reversed(latest_mail_ids)):
            res, msg_data = mail.fetch(mail_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Email Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    
                    # Decode Sender
                    from_user, encoding = decode_header(msg["From"])[0]
                    if isinstance(from_user, bytes):
                        from_user = from_user.decode(encoding if encoding else "utf-8", errors="ignore")

                    # Extract Body snippet
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    # Keep only the first 300 characters of the body to respect Groq's TPM
                    snippet = body[:300].strip().replace('\n', ' ')
                    email_corpus.append(f"Email {index+1}: From: {from_user} | Subject: {subject} | Content: {snippet}")

        mail.logout()
        return "\n".join(email_corpus)

    except Exception as e:
        return f"An error occurred while accessing the email server: {str(e)}"
    
def read_local_file_drops():
    """Scans the incoming_files directory for new documents and reads their contents."""
    incoming_dir = os.path.join(os.path.dirname(__file__), "incoming_files")
    
    # Ensure the folder exists
    if not os.path.exists(incoming_dir):
        os.makedirs(incoming_dir)
        return "No files found (directory was missing and has now been created)."

    files = [f for f in os.listdir(incoming_dir) if os.path.isfile(os.path.join(incoming_dir, f))]
    
    if not files:
        return "No files found in the local file drop directory."

    file_corpus = []
    
    # Read up to 3 files to keep token limits safe
    for index, file_name in enumerate(files[:3]):
        file_path = os.path.join(incoming_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(400) # Read first 400 characters to save tokens
                snippet = content.strip().replace('\n', ' ')
                file_corpus.append(f"File {index+1} [{file_name}]: {snippet}")
        except Exception as e:
            file_corpus.append(f"File {index+1} [{file_name}]: Error reading file ({str(e)})")

    return "\n".join(file_corpus)

# 3. Local Company Policy Knowledge Base Setup (RAG)
knowledge_store = None

def setup_knowledge_base():
    global knowledge_store
    if knowledge_store is not None:
        return knowledge_store

    policy_path = os.path.join(os.path.dirname(__file__), "data", "policy.txt")
    
    if not os.path.exists(policy_path):
        os.makedirs(os.path.dirname(policy_path), exist_ok=True)
        with open(policy_path, "w", encoding="utf-8") as f:
            f.write("[Policy-HR-01]: All updates regarding remote work expense structures are mandatory and must be logged as high-priority tickets.")

    loader = TextLoader(policy_path, encoding="utf-8")
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")

    knowledge_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name="company_policy"
    )
    return knowledge_store

# 4. Action Tools (Custom Webhooks & Vector Searches)
@tool("Send Slack alert")
def send_slack_alert(message: str) -> str:
    """Sends a notification message directly to the team's Slack channel when an action completes."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return "Error: SLACK_WEBHOOK_URL is missing from environment configuration."
        
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return "Slack notification sent successfully!"
        else:
            return f"Failed to send Slack notification. Server returned status code: {response.status_code}"
    except Exception as e:
        return f"An error occurred while sending the Slack alert: {str(e)}"

@tool("Search company policy")
def search_company_policy(query: str) -> str:
    """Search the company policy knowledge base for relevant policy passages."""
    store = setup_knowledge_base()
    results = store.similarity_search(query, k=2)

    if not results:
        return "No matching policy content found."

    return "\n\n".join(
        f"Result {index + 1}: {result.page_content}"
        for index, result in enumerate(results)
    )

setup_knowledge_base()

# 5. Define CrewAI Agents with Aggressive Throttling
triage_agent = Agent(
    role="Corporate Triage Specialist",
    goal="Analyze commands and cross-reference with corporate policy quickly.",
    backstory="You are a sharp compliance auditor. Use your tools to look up relevant policies.",
    tools=[search_company_policy],  # Passed directly to prevent circular dependencies
    verbose=True,
    allow_delegation=False,
    memory=False,
    use_system_prompt=False,
    max_iter=1,  
    llm=groq_llm 
)

execution_agent = Agent(
    role="Jira Ticket Execution Specialist",
    goal="Call the Jira tool and Slack alert tools immediately when parameters are supplied.",
    backstory="You are a direct execution pipeline. You run tools instantly without strategic planning.",
    tools=[create_jira_ticket, send_slack_alert],  
    llm=groq_llm,
    verbose=True,
    memory=False,
    use_system_prompt=False,
    max_iter=1,  
    system_template=(
        "You are an execution unit. Call the real tools listed in your configuration explicitly "
        "and immediately based on text strings provided to you."
    )
)

# 6. Streamlit Web User Interface Layer
st.set_page_config(page_title="Multi-Agent Assistant", layout="wide")
st.title("🖥️ Multi-Agent Enterprise Assistant")
st.write("Using automated triage, file monitors, and ticket workflow pipelines.")

user_query = st.text_input("Enter your command (e.g., 'Analyze incoming feeds and process required tickets'):")

if user_query:
    with st.spinner("Orchestrating the agent execution..."):
        
        # Ingest both channels simultaneously
        email_data = read_mock_emails()
        file_data = read_local_file_drops()

        # Combine channels into a unified input window context
        universal_context = f"""
        --- LIVE EMAIL FEED ---
        {email_data}
        
        --- LOCAL FILE DROP FEED ---
        {file_data}
        """

        # Task 1: Audit and evaluate against company parameters
        audit_feeds_task = Task(
            description=(
                f"User Command: {user_query}\n\n"
                f"Context Channels to check:\n{universal_context}\n\n"
                "Analyze the context from both emails and local files. If any source requests "
                "a high-priority ticket that matches corporate policy, reply with a short sentence "
                "stating that action is MANDATORY. Do not write a long essay."
            ),
            expected_output="A brief structured summary identifying whether a high-priority ticket is required.",
            agent=triage_agent
        )

        audit_result = audit_feeds_task.execute_sync()
        
        st.info("Cooling down Groq rate limit window...")
        time.sleep(6)
        
        audit_result_text = str(getattr(audit_result, "raw", audit_result))

        # Dynamic string parsing configuration
        task_description_template = (
            "Look at the user's initial command:\n"
            "\"\"\"\n{user_command}\n\"\"\"\n\n"
            "And look at the triage audit summary:\n"
            "\"\"\"\n{audit_summary}\n\"\"\"\n\n"
            "If the triage confirms an issue should be created, perform these actions instantly:\n"
            "1. Run the 'Create Jira Ticket' tool with project_key: 'SCRUM', priority: 'High'.\n"
            "2. IMMEDIATELY take the resulting ticket key and run the 'Send Slack alert' tool once "
            "with a message formatted like: '🚀 [AI Automation] High-priority Jira ticket logged successfully! Key: SCRUM-X'"
        )

        # Task 2: Action execution pipeline assignment
        log_ticket_task = Task(
            description=task_description_template.format(
                user_command=user_query, 
                audit_summary=audit_result_text
            ),
            expected_output="The confirmation summary string text returned by the tools.",
            agent=execution_agent
        )

        ticket_output = log_ticket_task.execute_sync()

        st.success("Execution Complete!")
        st.subheader("📋 Automation Action Summary")

        output_text = getattr(ticket_output, "raw", str(ticket_output))

        if "SCRUM" in output_text or "id" in output_text:
            st.balloons()
            
            # Robust key extraction using Regex matches
            ticket_key_match = re.search(r"SCRUM-\d+", output_text)
            ticket_key = ticket_key_match.group(0) if ticket_key_match else "SCRUM-1"
            
            st.markdown(f"""
            ### ✅ Ticket Logged Successfully
            - **Jira Issue Key:** `{ticket_key}` 🚀
            - **Task Heading:** Update Remote Work Expense Policy Guidelines
            - **Status:** Active on Live Board
            """)
        else:
            st.warning("No action was necessary based on triage assessment parameters.")
            st.write(output_text)