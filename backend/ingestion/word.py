# backend/ingestion/word.py
import docx

def parse_docx(file_path: str) -> list:
    """Extracts structural text blocks from Word documents"""
    chunks = []
    try:
        doc = docx.Document(file_path)
        # Combine blocks of text into meaningful paragraph strings
        current_chunk = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                current_chunk.append(text)
                # Chunk documents roughly every 4 paragraphs to keep vector contexts tight
                if len(current_chunk) >= 4:
                    chunks.append({
                        "text": "\n".join(current_chunk),
                        "metadata": {"type": "docx"}
                    })
                    current_chunk = []
                    
        if current_chunk:
            chunks.append({
                "text": "\n".join(current_chunk),
                "metadata": {"type": "docx"}
            })
        return chunks
    except Exception as e:
        print(f"[ERROR] [DOCX Parser Error]: {str(e)}")
        return []