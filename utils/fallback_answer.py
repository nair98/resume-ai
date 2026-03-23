import re


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