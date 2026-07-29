# backend/ingest_docs.py
import os
import chromadb
from chromadb.utils import embedding_functions

# Define pathways matching your folder layout
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "incoming_files")
CHROMA_PATH = os.path.join(BASE_DIR, "backend", "chroma_db")

# Initialize ChromaDB persistent storage client
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# Using the standard default embedding function (SentenceTransformers framework style)
default_ef = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name="compliance_vectors", 
    embedding_function=default_ef
)

def chunk_text(text, max_chars=1000, overlap=200):
    """Splits long compliance documents into clean overlapping vector segments."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start += max_chars - overlap
    return chunks

def run_ingestion_pipeline():
    print(f"📁 Scanning target vectors directory: '{TARGET_DIR}'...")
    
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"[INFO] Created empty '{TARGET_DIR}' folder. Drop your .txt or .log files here!")
        return

    supported_files = [f for f in os.listdir(TARGET_DIR) if f.endswith(('.txt', '.log', '.md'))]
    
    if not supported_files:
        print("ℹ️ No new documentation signatures found in 'incoming_files/'. Ingestion standby.")
        return

    for file_name in supported_files:
        file_path = os.path.join(TARGET_DIR, file_name)
        print(f"📖 Processing tracking document: {file_name}...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
            
        if not raw_content.strip():
            continue
            
        chunks = chunk_text(raw_content)
        
        # Prepare vector data payloads
        documents = []
        metadatas = []
        ids = []
        
        for index, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({"source": file_name})
            ids.append(f"{file_name}_chunk_{index}")
            
        # Push batch vectors directly down to storage layer
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"[OK] Successfully ingested {len(chunks)} text vector vectors for {file_name}.")
        
    print("\n🚀 Database synchronization successful! Knowledge matrix is fully optimized.")

if __name__ == "__main__":
    run_ingestion_pipeline()