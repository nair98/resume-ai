import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from main import app
from utils.vector_store import DOCUMENTS, VECTORS

client = TestClient(app)


def reset_memory():
    DOCUMENTS.clear()
    VECTORS.clear()


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Resume AI Production Running"


def test_upload_txt_resume():
    reset_memory()

    file_content = b"Name: Siddharth Nair\nSkills: Python, FastAPI\nExperience: 3 years"
    response = client.post(
        "/upload-resume",
        files={"file": ("resume.txt", file_content, "text/plain")}
    )

    assert response.status_code == 200
    body = response.json()
    assert "stored successfully" in body["message"].lower()
    assert body["total_documents"] == 1


def test_ask_query_after_upload():
    reset_memory()

    file_content = b"Name: Siddharth Nair\nSkills: Python, FastAPI\nExperience: 3 years"
    client.post(
        "/upload-resume",
        files={"file": ("resume.txt", file_content, "text/plain")}
    )

    response = client.post("/ask", json={"query": "what skills does nair have"})
    assert response.status_code == 200

    body = response.json()
    assert "results" in body
    assert len(body["results"]) >= 1


def test_fallback_for_irrelevant_query():
    reset_memory()

    file_content = b"Name: Siddharth Nair\nSkills: Python, FastAPI\nExperience: 3 years"
    client.post(
        "/upload-resume",
        files={"file": ("resume.txt", file_content, "text/plain")}
    )

    response = client.post("/ask", json={"query": "who is shanaya"})
    assert response.status_code == 200

    body = response.json()
    assert "message" in body
    assert body["message"] == "Cannot answer from the uploaded document."