import os
from vector_storage import ingest_document

# 1. Define the directory where your raw text policies will live
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_source_files")

# 2. Sample corporate rule profiles matching your system logs
DEFAULT_POLICIES = {
    "Security_Rules.txt": (
        "Security Policy SR-4A: Infrastructure Access Control.\n"
        "All external third-party contractors, vendors, and off-site developers "
        "are strictly required to utilize secure VPN Gate 4A for all internal server access. "
        "Connecting without using VPN Gate 4A bypasses structural network firewalls and poses a "
        "critical risk to corporate integrity. Failure to comply results in immediate account lockdown."
    ),
    "Enterprise_Policy.txt": (
        "Enterprise Network Protocol EN-2222: Remote Management Boundaries.\n"
        "All internal and production server remote SSH connections must be routed exclusively through port 2222. "
        "Standard port 22 is disabled across the entire corporate network topology to mitigate automated brute-force "
        "attacks and prevent unauthorized lateral movements. Any connection attempt detected on port 22 is flagged "
        "automatically as an intrusion event."
    )
}

def execute_vector_seeding(user_id: int):
    # Ensure the policy directory exists on disk
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    
    print("🚀 Initiating GuardCore Knowledge Vector Ingestion Sequence...")
    
    for file_name, default_content in DEFAULT_POLICIES.items():
        file_path = os.path.join(KNOWLEDGE_DIR, file_name)
        
        # If the text file doesn't exist yet, generate it programmatically
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(default_content)
            print(f"📝 Created foundational baseline file: {file_name}")
            
        # Read the file text content cleanly
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        # Dispatch to our vector_storage processor matrix
        ingest_document(file_name, raw_text, user_id=user_id)
        
    print("\n🏁 Vector database seeding completed successfully! ChromaDB is primed.")

if __name__ == "__main__":
    seed_user_id = os.getenv("SEED_USER_ID")
    if not seed_user_id:
        raise SystemExit("SEED_USER_ID is required so seeded vectors are scoped to a user.")
    execute_vector_seeding(user_id=int(seed_user_id))
