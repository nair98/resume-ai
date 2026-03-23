import logging
from io import BytesIO
from fastapi import HTTPException

import pdfplumber
import docx

logger = logging.getLogger("parser")


# ----------------------------
# PDF Extraction
# ----------------------------
def extract_text_pdf(content: bytes, filename: str) -> str:
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        if not text.strip():
            logger.warning(f"PDF '{filename}' has no extractable text")

        return text or ""

    except Exception as e:
        logger.exception(f"Failed to extract PDF '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Failed to parse PDF")


# ----------------------------
# DOCX Extraction
# ----------------------------
def extract_text_docx(content: bytes, filename: str) -> str:
    try:
        doc = docx.Document(BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        if not text.strip():
            logger.warning(f"DOCX '{filename}' has no text")

        return text or ""

    except Exception as e:
        logger.exception(f"Failed to extract DOCX '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Failed to parse DOCX")


# ----------------------------
# TXT Extraction
# ----------------------------
def extract_text_txt(content: bytes, filename: str) -> str:
    try:
        text = content.decode("utf-8")

        if not text.strip():
            logger.warning(f"TXT '{filename}' is empty")

        return text or ""

    except Exception as e:
        logger.exception(f"Failed to read TXT '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Failed to read TXT file")


# ----------------------------
# MAIN EXTRACTOR (ENTRY POINT)
# ----------------------------
async def extract_text(file) -> str:
    """
    Detect file type and extract text.
    Supports PDF, DOCX, TXT.
    """

    filename = file.filename
    content_type = (file.content_type or "").lower()

    logger.info(f"Extracting '{filename}' | Type: {content_type}")

    try:
        # ✅ READ FILE ONLY ONCE (critical fix)
        content = await file.read()

        if not content:
            logger.warning(f"Empty file uploaded: {filename}")
            raise HTTPException(status_code=400, detail="Empty file")

        # Route based on content type
        if content_type == "application/pdf":
            text = extract_text_pdf(content, filename)

        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            text = extract_text_docx(content, filename)

        elif content_type == "text/plain":
            text = extract_text_txt(content, filename)

        else:
            logger.error(f"Unsupported file type: {content_type}")
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # ✅ FINAL SAFETY CHECK
        if not text.strip():
            logger.warning(f"No readable content in '{filename}'")
            raise HTTPException(status_code=400, detail="No readable content found")

        return text

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Unexpected parsing error for '{filename}': {e}")
        raise HTTPException(status_code=500, detail="Internal parsing error")