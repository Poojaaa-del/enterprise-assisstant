# backend/agents/document_parser.py
"""
DocumentParserAgent
Routes uploaded file bytes to the correct ingestion module, applies
~500-token chunking with 50-token overlap, and stamps user_id into metadata.
"""
import os
import io
import tempfile
from typing import List

import tiktoken

from ingestion.pdf import parse_pdf
from ingestion.word import parse_docx
from ingestion.excel import parse_spreadsheet
from ingestion.text import parse_txt


# Token encoder for chunk-size calculations (cl100k_base covers GPT-4 / Groq tokenisation)
_ENCODER = tiktoken.get_encoding("cl100k_base")

CHUNK_TOKENS  = 500  # target chunk size in tokens
OVERLAP_TOKENS = 50  # overlap between adjacent chunks


def _chunk_text(
    text: str,
    filename: str,
    user_id: int,
    base_metadata: dict,
    department: str = "General",
    permitted_role: str = "USER",
) -> List[dict]:
    """
    Splits a raw text string into overlapping token-window chunks and
    attaches filename + user_id + department to every chunk's metadata.
    """
    tokens = _ENCODER.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text   = _ENCODER.decode(chunk_tokens).strip()

        if chunk_text:
            meta = {
                **base_metadata,
                "filename":   filename,
                "user_id":    user_id,
                "department": str(department),    # RBAC department scoping
                "permitted_role": str(permitted_role),
            }
            chunks.append({"text": chunk_text, "metadata": meta})

        if end == len(tokens):
            break
        start += CHUNK_TOKENS - OVERLAP_TOKENS

    return chunks


class DocumentParserAgent:
    """
    Accepts raw file bytes plus filename, routes to the appropriate ingestion
    parser, applies chunking with overlap, and returns user-scoped chunk objects.
    """

    def parse(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: int,
        department: str = "General",
        permitted_role: str = "USER",
    ) -> List[dict]:
        """
        Returns a list of chunk dicts:
            [{ "text": "...", "metadata": { "page": 1, "filename": "...", "user_id": "5", "department": "HR" } }]
        """
        ext = os.path.splitext(filename.lower())[1]
        chunks: List[dict] = []

        # Write bytes to a temp file so the parsers can open it by path
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            if ext == ".pdf":
                raw_chunks = parse_pdf(tmp_path)
            elif ext in (".docx", ".doc"):
                raw_chunks = parse_docx(tmp_path)
            elif ext in (".xlsx", ".xls", ".csv"):
                raw_chunks = parse_spreadsheet(tmp_path, filename)
            elif ext == ".txt":
                raw_chunks = parse_txt(tmp_path)
            elif ext in (".png", ".jpg", ".jpeg"):
                # Direct Image Parse fallback using Gemini 2.5 Flash if available
                img_desc = f"Uploaded image: {filename}"
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    try:
                        from google import genai
                        from google.genai import types
                        client = genai.Client(api_key=api_key)
                        res = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[
                                "Describe this uploaded image diagram/chart in detail for indexing.",
                                types.Part.from_bytes(data=file_bytes, mime_type=f"image/{ext.lstrip('.')}")
                            ]
                        )
                        if res.text:
                            img_desc = res.text.strip()
                    except Exception as img_err:
                        print(f"[WARNING] [Image Parse] Gemini image processing bypass: {img_err}")
                raw_chunks = [{"text": img_desc, "metadata": {"type": "image", "is_ocr": True}}]
            else:
                print(f"[WARNING] [DocumentParserAgent] Unsupported type: {ext}")
                return []

            # Re-chunk each parser output into token-window segments
            for raw in raw_chunks:
                base_meta = raw.get("metadata", {})
                sub_chunks = _chunk_text(
                    text          = raw.get("text", ""),
                    filename      = filename,
                    user_id       = user_id,
                    base_metadata = base_meta,
                    department    = department,
                    permitted_role= permitted_role,
                )
                chunks.extend(sub_chunks)

        except Exception as exc:
            print(f"[ERROR] [DocumentParserAgent] Parsing failed for {filename}: {exc}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return chunks

