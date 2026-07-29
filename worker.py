import os
import re
import time
import requests
import imaplib
import email
import logging
from email.header import decode_header
from dotenv import load_dotenv

import crewai.llms.cache as _crewai_cache
# Override cache breakpoints safely
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

from crewai import Agent, Task, LLM
from crewai.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from tools import create_jira_ticket

# Setup logging to see exactly what the worker is doing in the background
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("automation_worker.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Initialize Groq Engine
groq_llm = LLM(
    model="groq/llama-3.3-70b-versatile",  
    base_url="https://api.groq.com/openai/v1", 
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=800
)

# ----------------- INGESTION CHANNELS -----------------
def read_live_emails():
    username = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    imap_server = os.environ.get("EMAIL_IMAP_SERVER", "imap.gmail.com")

    if not username or not password:
        return "Error: Email credentials missing."

    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select("inbox")
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != "OK" or not messages[0]:
            mail.logout()
            return "No new unread emails."

        mail_ids = messages[0].split()
        latest_mail_ids = mail_ids[-3:]
        email_corpus = []

        for index, mail_id in enumerate(reversed(latest_mail_ids)):
            res, msg_data = mail.fetch(mail_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    from_user, encoding = decode_header(msg["From"])[0]
                    if isinstance(from_user, bytes):
                        from_user = from_user.decode(encoding if encoding else "utf-8", errors="ignore")

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    snippet = body[:300].strip().replace('\n', ' ')
                    email_corpus.append(f"Email {index+1}: From: {from_user} | Subject: {subject} | Content: {snippet}")

        mail.logout()
        return "\n".join(email_corpus)
    except Exception as e:
        return f"Email read failure: {str(e)}"

def read_local_file_drops():
    incoming_dir = os.path.join(os.path.dirname(__file__), "incoming_files")
    if not os.path.exists(incoming_dir):
        os.makedirs(incoming_dir)
        return "No files found."

    files = [f for f in os.listdir(incoming_dir) if os.path.isfile(os.path.join(incoming_dir, f))]
    if not files:
        return "No files found."

    file_corpus = []
    for index, file_name in enumerate(files[:3]):
        file_path = os.path.join(incoming_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                snippet = f.read(400).strip().replace('\n', ' ')
                file_corpus.append(f"File {index+1} [{file_name}]: {snippet}")
            
            # Archive file after processing so it doesn't loop forever
            os.rename(file_path, os.path.join(incoming_dir, f"processed_{int(time.time())}_{file_name}"))
        except Exception as e:
            file_corpus.append(f"File {index+1} [{file_name}]: Error ({str(e)})")

    return "\n".join(file_corpus)

# ----------------- KNOWLEDGE BASE & TOOLS -----------------
knowledge_store = None

def setup_knowledge_base():
    global knowledge_store
    if knowledge_store is not None:
        return knowledge_store

    policy_path = os.path.join(os.path.dirname(__file__), "data", "policy.txt")
    loader = TextLoader(policy_path, encoding="utf-8")
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(loader.load())
    
    knowledge_store = Chroma.from_documents(
        documents=chunks,
        embedding=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
        persist_directory=os.path.join(os.path.dirname(__file__), "chroma_db"),
        collection_name="company_policy"
    )
    return knowledge_store

@tool("Send Slack alert")
def send_slack_alert(message: str) -> str:
    """Sends a message to the Slack channel."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url: return "Missing URL."
    try:
        res = requests.post(webhook_url, json={"text": message})
        return "Slack alert dispatched!" if res.status_code == 200 else f"Failed: {res.status_code}"
    except Exception as e: return str(e)

@tool("Search company policy")
def search_company_policy(query: str) -> str:
    """Searches corporate guidelines."""
    store = setup_knowledge_base()
    results = store.similarity_search(query, k=2)
    return "\n\n".join(f"Result {i+1}: {r.page_content}" for i, r in enumerate(results)) if results else "No policy found."

# ----------------- CORE PIPELINE EXECUTION -----------------
def execute_agent_pipeline():
    logging.info("Starting background feed evaluation loop...")
    
    email_feed = read_live_emails()
    file_feed = read_local_file_drops()

    if ("No new unread emails" in email_feed or "Error:" in email_feed) and "No files found" in file_feed:
        logging.info("Feeds are quiet. No automation actions required.")
        return

    universal_context = f"--- EMAILS ---\n{email_feed}\n\n--- LOCAL FILES ---\n{file_feed}"

    # Agents Setup
    triage_agent = Agent(
        role="Corporate Triage Specialist",
        goal="Audit commands against corporate policy.",
        backstory="You check local files/emails for high priority policy items.",
        tools=[search_company_policy],
        verbose=False,
        max_iter=1,
        llm=groq_llm
    )

    execution_agent = Agent(
        role="Jira Ticket Execution Specialist",
        goal="Call tools immediately.",
        backstory="You run Jira logs and Slack notification requests.",
        tools=[create_jira_ticket, send_slack_alert],
        llm=groq_llm,
        verbose=False,
        max_iter=1,
        system_template="Execute tools immediately based on text strings given to you."
    )

    # Task Chain
    audit_task = Task(
        description=f"Analyze this data environment context:\n{universal_context}\n\nDetermine if an HR policy update action is MANDATORY.",
        expected_output="Short confirmation if ticket logging is mandatory.",
        agent=triage_agent
    )

    audit_result = str(getattr(audit_task.execute_sync(), "raw", audit_task.execute_sync()))
    
    # Respect Groq TPM Window between agent tasks
    time.sleep(6)

    log_task = Task(
        description=(
            f"Audit Context: {audit_result}\n\n"
            "If mandated, perform these steps instantly:\n"
            "1. Run 'Create Jira Ticket' (project_key: 'SCRUM', priority: 'High')\n"
            "2. Take the output ticket key and run 'Send Slack alert'."
        ),
        expected_output="Execution tool confirmations.",
        agent=execution_agent
    )

    result_output = str(getattr(log_task.execute_sync(), "raw", log_task.execute_sync()))
    logging.info(f"Pipeline Execution Summary: {result_output}")

# ----------------- CONTINUOUS CLOCK TICKER -----------------
if __name__ == "__main__":
    logging.info("Background Ticker Engine fully initialized. Running continuously...")
    
    # Run intervals (10 minutes = 600 seconds)
    INTERVAL_SECONDS = 600 
    
    try:
        while True:
            try:
                execute_agent_pipeline()
            except Exception as e:
                logging.error(f"Error encountered during background cycle: {str(e)}")
            
            logging.info(f"Sleeping for {INTERVAL_SECONDS // 60} minutes until next cycle...")
            time.sleep(INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logging.info("Background daemon shut down gracefully by user command.")