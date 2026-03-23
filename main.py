import asyncio
import time
import tracemalloc
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from utils.parser import extract_text
from utils.vector_store import add_document, search, DOCUMENTS

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
        response = {
            "answer": " ".join([doc for _, doc in results])[:1500],  # combined snippet
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