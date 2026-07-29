# backend/ingestion/pdf.py
import os
import io
import fitz  # PyMuPDF

# Try importing PIL & pytesseract for OCR fallback
try:
    from PIL import Image
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

# Try importing Google GenAI SDK for visual multimodal summaries
try:
    from google import genai as genai_new  # type: ignore
    from google.genai import types as genai_types  # type: ignore
    GENAI_VERSION = "new"
except ImportError:
    try:
        import google.generativeai as genai_legacy  # type: ignore
        GENAI_VERSION = "legacy"
    except ImportError:
        GENAI_VERSION = None


def parse_pdf(file_path: str) -> list:
    """Extracts text and page metadata from PDF files with OCR & Multimodal Vision Fallback"""
    chunks = []
    api_key = os.getenv("GEMINI_API_KEY")

    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text().strip()
            is_ocr = False

            # Trigger OCR & Vision Fallback if extracted text is empty or less than 20 characters
            if len(text) < 20:
                is_ocr = True
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                ocr_text = ""
                vision_desc = ""

                # 1. Pytesseract OCR Extraction
                if PYTESSERACT_AVAILABLE:
                    try:
                        img = Image.open(io.BytesIO(img_bytes))
                        ocr_text = pytesseract.image_to_string(img).strip()
                    except Exception as ocr_err:
                        print(f"[WARNING] [PDF OCR] Pytesseract bypass on page {page_num + 1}: {ocr_err}")

                # 2. Gemini Multimodal Vision Summary
                if api_key:
                    try:
                        if GENAI_VERSION == "new":
                            client = genai_new.Client(api_key=api_key)
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[
                                    "Describe this scanned page, diagram, chart, or document layout in thorough technical prose for vector search indexing.",
                                    genai_types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                                ]
                            )
                            if response.text:
                                vision_desc = response.text.strip()
                        elif GENAI_VERSION == "legacy":
                            genai_legacy.configure(api_key=api_key)
                            model = genai_legacy.GenerativeModel('gemini-1.5-flash')
                            img_part = {"mime_type": "image/png", "data": img_bytes}
                            response = model.generate_content([
                                "Describe this scanned page, diagram, or chart in detail for technical document retrieval.",
                                img_part
                            ])
                            if response.text:
                                vision_desc = response.text.strip()
                    except Exception as vision_err:
                        print(f"[WARNING] [PDF Vision] Gemini Flash summary bypass on page {page_num + 1}: {vision_err}")

                # Combine extracted text signals
                parts = []
                if text:
                    parts.append(f"[Page Text]: {text}")
                if ocr_text:
                    parts.append(f"[OCR Text]: {ocr_text}")
                if vision_desc:
                    parts.append(f"[Visual Summary]: {vision_desc}")
                
                text = "\n\n".join(parts).strip()

            if text:
                chunks.append({
                    "text": text,
                    "metadata": {
                        "page_number": page_num + 1,
                        "type": "pdf",
                        "is_ocr": is_ocr
                    }
                })
        return chunks
    except Exception as e:
        print(f"[ERROR] [PDF Parser Error]: {str(e)}")
        return []
