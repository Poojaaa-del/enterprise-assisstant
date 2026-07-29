import os
import chromadb
from chromadb.utils import embedding_functions

# 1. Initialize Persistent Storage Matrix on local disk
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# 2. CRITICAL: Use the SAME embedding function as knowledge.py and retrieval.py.
#    All three modules MUST share the same embedding function AND collection name.
#    The old code used DefaultEmbeddingFunction + "guardcore_compliance_knowledge",
#    while knowledge.py / retrieval.py used SentenceTransformer + "guard_core_nodes".
#    That mismatch caused ingest_document() to write to a dead collection that
#    RetrievalAgent never queried, producing 0% RAG confidence on every query.
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 3. Secure or instantiate the shared core collection.
#    Name MUST match: knowledge.py and retrieval.py both use "guard_core_nodes".
collection = chroma_client.get_or_create_collection(
    name="guard_core_nodes",
    embedding_function=embedding_func
)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """
    Splits long compliance documents into overlapping windows so that
    sentences or context boundaries aren't clipped at arbitrary cutoffs.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def ingest_document(
    file_name: str,
    raw_content: str,
    user_id: int,
    classification: str = "GENERAL",
    permitted_role: str = "USER",
):
    """
    Chunks a text file, generates vector signatures, and commits them
    along with rich enterprise metadata tags into ChromaDB.
    """
    chunks = chunk_text(raw_content)

    documents = []
    metadatas = []
    ids = []

    for idx, chunk in enumerate(chunks):
        documents.append(chunk)
        # Enriched metadata architecture for hybrid filtering/RBAC
        metadatas.append({
            "source": file_name,
            "chunk_index": idx,
            "classification": classification,
            "permitted_role": permitted_role,
            # Store as str for consistent ChromaDB $eq comparisons
            "user_id": str(user_id),
        })
        ids.append(f"user_{user_id}_{file_name}_chunk_{idx}")

    # Use upsert (not add) so re-uploads don't crash with DuplicateIDException
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print(f"[OK] Indexed {len(chunks)} vectors from '{file_name}' [User: {user_id}, Role: {permitted_role}, Class: {classification}]")


def query_knowledge_vector(query_text: str, user_id: int, max_results: int = 3, user_role: str = "USER") -> dict:
    """
    Executes a semantic lookup with metadata-driven role constraints
    ensuring a user cannot view unauthorized documentation.
    """
    # user_id must be str to match metadata stored via ingest_document() and _bg_process_file.
    where_filter = {
        "$and": [
            {"permitted_role": user_role},
            {"user_id": str(user_id)},
        ]
    }

    results = collection.query(
        query_texts=[query_text],
        n_results=max_results,
        where=where_filter  # ChromaDB native metadata structural filtering
    )

    if not (results and results.get("documents") and len(results["documents"][0]) > 0):
        # Fallback directly to user_id filter if permitted_role tag differs
        results = collection.query(
            query_texts=[query_text],
            n_results=max_results,
            where={"user_id": str(user_id)}
        )

    if results and results.get("documents") and len(results["documents"][0]) > 0:
        combined_context = "\n\n---\n\n".join(results["documents"][0])
        citation = results["metadatas"][0][0].get("source", "Unknown Knowledge Source")
        return {"context": combined_context, "citation": citation}

    return {"context": "No documents found in your knowledge base for this query.", "citation": "None"}
