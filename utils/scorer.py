import re


def score_resume(text: str) -> dict:
    score = 0
    reasons = []

    name_match = re.search(r"name:\s*(.+)", text, re.IGNORECASE)
    skills_match = re.search(r"skills:\s*(.+)", text, re.IGNORECASE)
    exp_match = re.search(r"experience:\s*(.+)", text, re.IGNORECASE)

    if name_match:
        score += 20
        reasons.append("Name found")

    if skills_match:
        score += 40
        reasons.append("Skills section found")

    if exp_match:
        score += 40
        reasons.append("Experience section found")

    if score >= 80:
        summary = "Strong resume with key details present."
    elif score >= 50:
        summary = "Moderate resume quality with some important details present."
    else:
        summary = "Resume is missing important details."

    return {
        "resume_score": score,
        "summary": summary,
        "details": reasons
    }