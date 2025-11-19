import re
from typing import List


def sanitize_part(text: str, fallback: str = "untitled") -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return fallback

    cleaned = re.sub(r"\s+", "_", cleaned.lower())
    cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)

    return cleaned or fallback


def build_short_answers_text(short_answers: List[str]) -> str:
    answers_text = ""
    for idx, ans in enumerate(short_answers, start=1):
        answers_text += f"Answer {idx}:\n{ans}\n\n"
    return answers_text


def label_fit(score: float) -> str:
    if score >= 85:
        return "Strong fit"
    if score >= 65:
        return "Good fit"
    return "Weak fit"
