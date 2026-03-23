import math
from sentence_transformers import SentenceTransformer

# ----------------------------
# Load model once
# ----------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------------------
# In-memory storage
# ----------------------------
DOCUMENTS = []
VECTORS = []

# ----------------------------
# Add document
# ----------------------------
def add_document(text: str):
    if not text.strip():
        print("Skipping empty document")
        return

    DOCUMENTS.append(text)

    # Convert to Python list (fixes numpy issue)
    embedding = model.encode(text).tolist()
    VECTORS.append(embedding)

    print(f"Document added. Total documents: {len(DOCUMENTS)}")

# ----------------------------
# Cosine similarity
# ----------------------------
def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    # Force Python float
    return float(dot / (norm1 * norm2))

# ----------------------------
# Search documents
# ----------------------------
def search(query: str, top_k=3, min_score=0.2):
    if not VECTORS:
        print("No vectors stored yet")
        return []

    # Convert to list
    query_vec = model.encode(query).tolist()

    scores = [cosine_similarity(query_vec, vec) for vec in VECTORS]

    # Ensure all scores are Python floats
    scored_docs = [(float(score), doc) for score, doc in zip(scores, DOCUMENTS)]

    # Filter
    scored_docs = [sd for sd in scored_docs if sd[0] >= min_score]

    if not scored_docs:
        print("No relevant documents found for query:", query)
        return []

    # Sort
    scored_docs.sort(reverse=True, key=lambda x: x[0])

    return scored_docs[:top_k]