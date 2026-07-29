# backend/ingestion/text.py

def parse_txt(file_path: str) -> list:
    """Chunks raw text files by paragraph breaks"""
    chunks = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        raw_blocks = content.split("\n\n")
        for idx, block in enumerate(raw_blocks):
            cleaned = block.strip()
            if cleaned:
                chunks.append({
                    "text": cleaned,
                    "metadata": {
                        "block_index": idx,
                        "type": "txt"
                    }
                })
        return chunks
    except Exception as e:
        print(f"[ERROR] [TXT Parser Error]: {str(e)}")
        return []