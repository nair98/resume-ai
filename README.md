![CI](https://github.com/nair98/resume-ai/actions/workflows/ci.yml/badge.svg)
# AI Resume Scorer

A production-ready AI-powered Resume Scorer built with FastAPI that supports resume upload, semantic search, intelligent query handling, fallback mechanisms, performance logging, and automated smoke testing.

## Features
- Resume upload and text extraction
- Query-based semantic search over uploaded resume content
- Similarity score / percentage in responses
- Fallback handling for irrelevant queries
- Error handling and logging
- Request-level performance metrics (latency and memory usage)
- Automated smoke tests using pytest

## Tech Stack
- Python
- FastAPI
- Uvicorn
- Sentence Transformers
- Pytest

## Example Queries
- What skills does the candidate have?
- What is the candidate’s experience?
- Who is the candidate?

## Run Locally
```bash
uvicorn main:app --host 0.0.0.0 --port 8000

## 🏗 Architecture

- FastAPI backend handles API requests  
- Parser extracts resume text  
- Vector store performs semantic search  
- Query engine returns relevant results with similarity score  
- Fallback logic handles low-confidence queries  
- Logging middleware tracks performance metrics  
- CI pipeline ensures automated testing on every push  

### Swagger UI
![Swagger UI](screenshot.png)