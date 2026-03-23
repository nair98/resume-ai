import asyncio
import time
import tracemalloc
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from utils.parser import extract_text
from utils.vector_store import add_document, search, DOCUMENTS
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.fallback_answer import generate_fallback_answer
from utils.scorer import score_resume


def generate_fallback_answer(query: str, context: str) -> str:
    query_lower = query.lower()

    name_match = re.search(r"name:\s*(.+)", context, re.IGNORECASE)
    skills_match = re.search(r"skills:\s*(.+)", context, re.IGNORECASE)
    exp_match = re.search(r"experience:\s*(.+)", context, re.IGNORECASE)

    name = name_match.group(1).strip() if name_match else None
    skills = skills_match.group(1).strip() if skills_match else None
    experience = exp_match.group(1).strip() if exp_match else None

    if "skill" in query_lower:
        if skills:
            return f"The candidate has skills in {skills}."
        return "Cannot answer from the uploaded document."

    if "experience" in query_lower:
        if experience:
            return f"The candidate has {experience} of experience."
        return "Cannot answer from the uploaded document."

    if "who is" in query_lower or "name" in query_lower:
        if name:
            return f"The candidate is {name}."
        return "Cannot answer from the uploaded document."

    if name and skills and experience:
        return f"{name} has skills in {skills} and {experience} of experience."

    return "Cannot answer from the uploaded document."

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(query: str, context: str) -> str:
    prompt = f"""
You are a resume assistant.

Answer ONLY from the resume context below.
If answer is not present, say:
"Cannot answer from the uploaded document."

Resume:
{context}

Question:
{query}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Answer only from provided resume."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

# ----------------------------
# Logging setup
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("resume-scorer")

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="Production Resume Scorer")

# ----------------------------
# Pydantic model
# ----------------------------
class QueryRequest(BaseModel):
    query: str

# ----------------------------
# Middleware: Performance metrics
# ----------------------------
@app.middleware("http")
async def add_process_metrics(request: Request, call_next):
    start_time = time.time()
    tracemalloc.start()
    try:
        response = await call_next(request)
        return response
    finally:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        duration = time.time() - start_time
        logger.info(
            f"API Hit: {request.method} {request.url.path} | "
            f"Duration: {duration:.3f}s | "
            f"Memory Usage: {current / 1024:.2f}KB | Peak: {peak / 1024:.2f}KB | "
            f"Total Docs: {len(DOCUMENTS)}"
        )

# ----------------------------
# Root
# ----------------------------
@app.get("/")
async def root():
    return {"message": "Resume AI Production Running"}

# ----------------------------
# Upload resume
# ----------------------------
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        logger.info(f"Upload request: {file.filename} | Type: {file.content_type}")
        text = await extract_text(file)

        if not text.strip():
            logger.warning(f"No text found in {file.filename}")
            return JSONResponse(status_code=400, content={"error": "No text found in the uploaded resume"})

        add_document(text)
        logger.info(f"Stored '{file.filename}'. Total docs: {len(DOCUMENTS)}")
        return {"message": f"Document '{file.filename}' stored successfully", "total_documents": len(DOCUMENTS)}

    except Exception as e:
        logger.exception(f"Upload failed for '{file.filename}'")
        return JSONResponse(status_code=500, content={"error": str(e)})

# -------------------------
# score
# -------------------------
@app.post("/score")
async def score_uploaded_resume(file: UploadFile = File(...)):
    try:
        logger.info(f"Score request: {file.filename} | Type: {file.content_type}")
        text = await extract_text(file)

        if not text.strip():
            logger.warning(f"No text found in {file.filename}")
            return JSONResponse(status_code=400, content={"error": "No text found in the uploaded resume"})

        result = score_resume(text)

        logger.info(f"Scored '{file.filename}' successfully")
        return result

    except Exception as e:
        logger.exception(f"Scoring failed for '{file.filename}'")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ----------------------------
# Ask query
# ----------------------------
@app.post("/ask")
async def ask_question(request: QueryRequest):
    try:
        query = request.query.strip()
        logger.info(f"Query received: {query}")

        if not query:
            return JSONResponse(status_code=400, content={"error": "Query cannot be empty"})

        # ----------------------------
        # Retry/fallback logic
        # ----------------------------
        results = []
        retries = 2
        for attempt in range(1, retries + 1):
            try:
                results = search(query, top_k=3, min_score=0.10)
                break
            except Exception as e:
                logger.warning(f"Search attempt {attempt} failed: {e}")
                await asyncio.sleep(0.5)
        else:
            logger.error("All search attempts failed")
            return JSONResponse(status_code=500, content={"error": "Search service failed, try again later"})

        # ----------------------------
        # No results found
        # ----------------------------
        if not results or float(results[0][0]) < 0.30:
            return {
                "results": [],
                "message": "Cannot answer from the uploaded document."
            }

        # ----------------------------
        # Prepare response
        # ----------------------------
        context = " ".join([doc for _, doc in results])[:1500]
        fallback_used = False

        try:
            from utils.llm import generate_answer
            llm_answer = generate_answer(query, context)
        except Exception as e:
            logger.warning(f"LLM failed, using fallback answer: {e}")
            llm_answer = generate_fallback_answer(query, context)
            fallback_used = True

        top_score = float(results[0][0]) if results else 0

        response = {
            "answer": llm_answer,
            "confidence_score": round(top_score * 100, 2),
            "source": "Uploaded Resume",
            "fallback_used": fallback_used,
            "results": []
        }

        for idx, (score, doc) in enumerate(results, 1):
            snippet = doc[:500] + ("..." if len(doc) > 500 else "")
            response["results"].append({
                "doc_id": idx,
                "similarity_percentage": round(float(score) * 100, 2),
                "snippet": snippet
            })

        logger.info(f"Returned {len(response['results'])} results")
        return response

    except Exception as e:
        logger.exception("Error in /ask endpoint")
        return JSONResponse(status_code=500, content={"error": str(e)})