import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def generate_answer(query: str, context: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

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