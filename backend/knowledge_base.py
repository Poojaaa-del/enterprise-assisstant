# backend/knowledge_base.py
import os
import re

# Resolve path absolutely relative to this file's location (backend/)
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base_data")
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

def seed_default_knowledge():
    """Seeds default policies if the base directory is empty."""
    default_file = os.path.join(KNOWLEDGE_DIR, "security_policy.txt")
    if not os.path.exists(default_file):
        with open(default_file, "w", encoding="utf-8") as f:
            f.write("Enterprise Policy: All remote SSH connections must use port 2222.\n")
            f.write("Security Directive: Two-Factor Authentication (2FA) is mandatory for all enterprise dashboards.\n")

def clean_text_to_words(text: str) -> set:
    """Helper to clean punctuation and split text into a set of clean lowercase words."""
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return set(cleaned.split())

def search_knowledge(query: str, limit: int = 2):
    """
    Pure Python Keyword Search Fallback.
    """
    seed_default_knowledge()
    
    chunks = []
    if os.path.exists(KNOWLEDGE_DIR):
        for filename in os.listdir(KNOWLEDGE_DIR):
            if filename.endswith(".txt"):
                filepath = os.path.join(KNOWLEDGE_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        text = f.read()
                        # Split file into line-by-line chunks
                        for line in text.split("\n"):
                            line = line.strip()
                            if len(line) > 10:
                                chunks.append(line)
                except Exception as e:
                    print(f"Error reading reference file {filename}: {e}")

    # Clean the query to match words accurately
    query_words = clean_text_to_words(query)
    scored_chunks = []
    
    for chunk in chunks:
        chunk_words = clean_text_to_words(chunk)
        # Score based on intersecting words
        match_score = len(query_words.intersection(chunk_words))
        if match_score > 0:
            scored_chunks.append((match_score, chunk))
            
    # Sort descending by match relevancy score
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    results = [chunk for _, chunk in scored_chunks[:limit]]
    
    # If no keywords matched, return default context chunks as fallback
    if not results and chunks:
        results = chunks[:limit]
        
    return results